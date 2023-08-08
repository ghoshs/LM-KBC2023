import json
import openai
import ast
from file_io import *
from evaluate import *
import time
import random
import argparse
import requests

# This baseline uses GPT-3 to generate surface forms, and Wikidata's disambiguation API to produce entity identifiers

# Get an answer from the GPT-API
def GPT3response(q):
    response = openai.ChatCompletion.create(
        # model = "gpt-3.5-turbo",
        model = "gpt-4",
        messages=[{"role": "user", "content": q}],
        temperature=0,
        max_tokens=50,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    ) 
    response = response.choices[0].message.content

    response = response.splitlines()[0]
    if len(response)>0:
        if response[0] == " ":
            response = response[1:]
    print("Answer is \"" + response + "\"\n")
    try:    
        response = ast.literal_eval(response)
    except:
        response = []
    return response


def retry_GPT3response(q, initial_delay=1, curr_retry=0, max_retries=10):
    delay = initial_delay
    errors = tuple([openai.error.ServiceUnavailableError, openai.error.RateLimitError, openai.error.APIError, openai.error.Timeout])
    try:
        response = GPT3response(q)

    except errors as e:
        curr_retry += 1
        if curr_retry > max_retries:
            raise Exception("Max retries %d exceeded."%max_retries)

        delay *= 2 * (1 + random.random())

        time.sleep(delay)
        response = retry_GPT3response(q, delay, curr_retry, max_retries)
    return response
        

def disambiguation_baseline(item):
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={item}&language=en&format=json"
        data = requests.get(url).json()
        # Return the first id (Could upgrade this in the future)
        return data['search'][0]['id']
    except:
        return item

def run(args):
    openai.api_key = args.oaikey
    
    prefix = '''Paraguay, country-borders-country, ["Bolivia", "Brazil", "Argentina"]
    Cologne, CityLocatedAtRiver, ["Rhine"]
    Hexadecane, CompoundHasParts, ["carbon", "hydrogen"]
    Antoine Griezmann, FootballerPlaysPosition, ["forward"]
    ''' 

    print('Starting probing GPT-3 ................')

    train_df = read_lm_kbc_jsonl_to_df(Path(args.input))
    
    print (train_df)

    results = []

    if args.restart < len(train_df):
        for idx, row in train_df.iterrows():

            if args.restart >= 0 and idx < args.restart:
                continue
            print("Resuming at: ", args.restart)
            prompt = prefix + row["SubjectEntity"] + ", " + row["Relation"] + ", "
            print("Prompt is \"{}\"".format(prompt))
            result = {
                "SubjectEntityID": row["SubjectEntityID"],
                "SubjectEntity": row["SubjectEntity"],
                "Relation": row["Relation"],
                "ObjectEntitiesSurfaceForms": retry_GPT3response(prompt), 
                "ObjectEntitiesID": []
            }
            # special treatment of numeric relations, do not execute disambiguation
            if result["Relation"]=="PersonHasNumberOfChildren" or result["Relation"]=="SeriesHasNumberOfEpisodes":
                result["ObjectEntitiesID"] = result["ObjectEntitiesSurfaceForms"]
            # normal relations: execute Wikidata's disambiguation
            else:
                for s in result['ObjectEntitiesSurfaceForms']:
                    result["ObjectEntitiesID"].append(disambiguation_baseline(s))

            results.append(result)

            with open(Path(args.output), "a") as f:
                f.write(json.dumps(result) + "\n")
            # time.sleep(1)
    # save_df_to_jsonl(Path(args.output), results)

    print('Finished probing GPT_3 ................')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Model with Question and Fill-Mask Prompts")
    parser.add_argument("-i", "--input", type=str, required=True, help="Input (subjects) file")
    parser.add_argument("-o", "--output", type=str, required=True, help="Predictions (output) file")
    parser.add_argument("-k", "--oaikey", type=str, required=True, help="OpenAI API key")
    parser.add_argument("-r", "--restart", type=int, default=0, help="Index to restart probing")
    #parser.add_argument("-f", "--few_shot", type=int, default=5, help="Number of few-shot examples (default: 5)")
    #parser.add_argument("--train_data", type=str, required=True, help="CSV file containing train data for few-shot examples (required)")

    args = parser.parse_args()

    run(args)