import json
import ast
import time
import re
import argparse
import requests
import openai
import random
from file_io import *
from evaluate import *

# This baseline uses GPT-3 to generate surface forms, and Wikidata's disambiguation API to produce entity identifiers

noble_map = {"physics": "Q38104", "chemistry": "Q44585", "literature": "Q37922", "peace": "Q35637", "medicine": "Q80061", "physiology": "Q80061", "economics": "Q47170"}

def set_prefix(relation, modified_relation, n_example=0):
    examples = {
        ## Instantiate with k-examples per relation to be used for few-shot probe.
        ## Not used in this setup
    }
    if n_example == 0:
        return ""
    else:
        assert examples[relation]
        train_eg = examples[relation]
        prefix = "(\"" +train_eg["SubjectEntity"] + "\", \"" + modified_relation + "\", "+json.dumps(train_eg["ObjectEntities"])+"). \n"
        return prefix


def extract_answer(response, subject, relation):
    response = response.choices[0].message.content
    response = [answer for answer in response.splitlines() if len(answer.strip())>0]

    for idx, r in enumerate(response):
        try:
            literal = ast.literal_eval(r)
        except:
            literal = re.findall('"([^"]*)"', r)
            if len(literal) > 2 and literal[0] == subject and literal[1] == relation:
                if len(literal) == 2:
                    literal = []
                else:
                    literal = literal[2:]
        if type(literal) == tuple:
            response[idx] = literal[-1]
        else:
            response[idx] = literal

    print(response)
    finalresponse = []
    for r in response:
        if isinstance(r, list):
            finalresponse += r
        else:
            finalresponse.append(str(r))

    return finalresponse


# Get an answer from the GPT-API
def GPT3response(model_name, q, subject, relation):
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[
            {"role": "user", "content": q}],
        temperature=0,
        max_tokens=200,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print("response is: ", response)    
    finalresponse = extract_answer(response, subject, relation)
    print("Answer is \"", finalresponse, "\"\n")
    return finalresponse


def retry_GPT3response(model_name, q, subject, relation, initial_delay=1, curr_retry=0, max_retries=10):
    delay = initial_delay
    errors = tuple([openai.error.ServiceUnavailableError, openai.error.RateLimitError, openai.error.APIError, openai.error.Timeout])
    try:
        response = GPT3response(model_name, q, subject, relation)

    except errors as e:
        curr_retry += 1
        if curr_retry > max_retries:
            raise Exception("Max retries %d exceeded."%max_retries)

        delay *= 2 * (1 + random.random())

        time.sleep(delay)
        response = retry_GPT3response(model_name, q, subject, relation, delay, curr_retry, max_retries)
    return response
        

def disambiguation_baseline(item):
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={item}&language=en&format=json"
        data = requests.get(url).json()
        # Return the first id (Could upgrade this in the future)
        return data['search'][0]['id']
    except:
        return ""


def get_wd_type(wd_ids):
    url = "https://query.wikidata.org/sparql"
    query = '''
SELECT ?obj ?instanceLabel {
  ?obj wdt:P31 ?instance.
  VALUES ?obj {'''+' '.join(["wd:"+o for o in wd_ids])+'''}
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}'''
    try:
        data = requests.get(url, params={"format": "json", "query": query})
        data = data.json()
    except Exception as e:
        print(e)
        print(wd_ids)
        data = {}
    labels = {o: [] for o in wd_ids}
    if "results" in data and "bindings" in data["results"]:
        for item in data["results"]["bindings"]:
            label = item["instanceLabel"]["value"]
            if len(label) > 0:
                wd_id = item["obj"]["value"].split("/")[-1] 
                labels[wd_id].append(label)
    return labels


def nl_relation(org_relation, modified_relation):
    relation = re.sub('([A-Z][a-z]+)', r' \1', org_relation).strip().lower()
    relation = relation.split(" ")
    subject_type = relation[0]
    relation = " ".join(relation[1:])
    if modified_relation==1:
        if relation == "has member":
            relation = "has members"
        if relation == "located at river":
            relation = "is located at river"
        if relation == "has parts" and subject_type == "compound":
            relation = "has elements"
        if relation == "has states":
            relation = "has provinces"
        if relation == "has spouse":
            relation = "has spouses"
            
        if relation == "plays instrument":
            relation = "plays instruments"
        if relation == "speaks language":
            relation = "speaks languages"
        if relation == "basins country":
            relation = "has basin countries"
        
        # # switch off at test
        # if relation == "borders country":
        #     relation = "borders countries"

        # if relation == "has official language":
        #     relation = "has official languages"
        # if relation == "cause of death":
        #     relation = "has causes of death"
        # if relation == "has autobiography":
        #     relation = "has autobiographies"
        # if relation == "has employer":
        #     relation = "has employers"
        # if relation == "has nobel prize" or relation == "has noble prize":
        #     relation == "has nobel prizes"
        # if relation == "has profession":
        #     relation = "has professions"
        # if relation == "borders state":
        #     relation = "borders provinces"
    elif modified_relation == -1:
        relation = org_relation
    return relation


def probe_LLMS(input_df, restart=0, output=None, modified_relation=None, model_name=None):
    openai.api_key = args.oaikey
    
    results = []

    task = "Please fill the empty list, if necessary, to create a correct fact. Return a valid tuple.\n"
    # prefix = "Please fill the empty list in the following tuple to create a correct fact. Return a valid tuple.\n"
    # prefix = '''Paraguay, country-borders-country, ["Bolivia", "Brazil", "Argentina"]
    # Cologne, CityLocatedAtRiver, ["Rhine"]
    # Hexadecane, CompoundHasParts, ["carbon", "hydrogen"]
    # Antoine Griezmann, FootballerPlaysPosition, ["forward"]
    # ''' 

    print('Starting probing GPT-3 ................')

    for idx, row in input_df.iterrows():
        if restart > 0 and idx < restart:
            continue
        
        if modified_relation:
            print("Using alternative relation:")
        else:
            print("Using original relation:")
        relation = nl_relation(row["Relation"], modified_relation)
        print(row["Relation"], "-->", relation)

        prefix = set_prefix(row["Relation"], relation)

        prompt = prefix + task + "(\"" +row["SubjectEntity"] + "\", \"" + relation + "\", [])"
        print("Prompt is \"{}\"".format(prompt))

        response = retry_GPT3response(model_name, prompt, row["SubjectEntity"], relation, 0, 4)
        result = {
            "SubjectEntityID": row["SubjectEntityID"],
            "SubjectEntity": row["SubjectEntity"],
            "Relation": row["Relation"],
            "ObjectEntitiesSurfaceForms": response, 
            "ObjectEntitiesID": []
        }
        # special treatment of numeric relations, do not execute disambiguation
        if result["Relation"]=="PersonHasNumberOfChildren" or result["Relation"]=="SeriesHasNumberOfEpisodes":
            result["ObjectEntitiesID"] = result["ObjectEntitiesSurfaceForms"]
        # normal relations: execute Wikidata's disambiguation
        else:
            for s in result['ObjectEntitiesSurfaceForms']:
                if result["Relation"] == "PersonHasNoblePrize":
                    if 'nobel' not in s or 'nobel prize' not in s:
                        s = s + ' nobel prize'
                result["ObjectEntitiesID"].append(disambiguation_baseline(s))
                
        results.append(result)

        with open(Path(output), "a") as f:
            f.write(json.dumps(result) + "\n")
        # time.sleep(1)
    # save_df_to_jsonl(Path(args.output), results)
    return results

    print('Finished probing GPT_3 ................')


def get_correct_types(ObjectEntitiesID, surface_forms, obj_type=None):
    type_corrected = {}
    wikidata_types = get_wd_type(ObjectEntitiesID)
    time.sleep(2)
    for idx, obj in enumerate(ObjectEntitiesID):
        if not any([x==obj_type for x in wikidata_types[obj]]):
            surface_form = surface_forms[idx]
            if obj_type not in surface_form:
                type_corrected[obj] = disambiguation_baseline(surface_form.strip() + " " + obj_type)
            else:
                type_corrected[obj] = ""
    return type_corrected


def clean_objectID_predictions(results, output):
    clean_results = []
    for row in results:
        # only keep Wikidata object IDs which are not "N/A" or "unknown" or "anonymous" or "false" or "None" or integer values
        ObjectEntitiesID = []
        if not isinstance(row["ObjectEntitiesID"], list):
            row["ObjectEntitiesID"] = [row["ObjectEntitiesID"]]
        for idx, item in enumerate(row["ObjectEntitiesID"]):
            if isinstance(item, int):
                ObjectEntitiesID.append(str(item))
            else:
                try:
                    item = int(item)
                except ValueError:
                    if item.startswith("Q") and item not in ["Q929804", "Q24238356", "Q4233718", "Q5432619", "Q543287"]:
                        # surface form is none variant but entity linking to other overloaded terminology
                        if row["ObjectEntitiesSurfaceForms"][idx].lower() not in ["n/a", "n.a.", "none", "unknown", "false"]:
                            ObjectEntitiesID.append(str(item))
                    else:
                        ObjectEntitiesID.append("")
                else:
                    ObjectEntitiesID.append(str(item))
        if any([item.startswith("Q") for item in ObjectEntitiesID]):
            # If object == subject then keep object empty
            ObjectEntitiesID = [item for item in ObjectEntitiesID if item not in row["SubjectEntityID"]]
        
        if row["Relation"] == "CityLocatedAtRiver":
            type_corrected = get_correct_types(ObjectEntitiesID, row["ObjectEntitiesSurfaceForms"], obj_type="river")
            ObjectEntitiesID = [type_corrected[obj] if obj in type_corrected else obj for obj in ObjectEntitiesID]

        # remove empty strings
        ObjectEntitiesID = [item for item in ObjectEntitiesID if len(item) > 0]

        # Relation specific clean-up
        if row["Relation"] == "PersonHasNoblePrize" and len(row["ObjectEntitiesSurfaceForms"]) > 0 and len(ObjectEntitiesID) == 0:
            for obj in row["ObjectEntitiesSurfaceForms"]:
                for word in obj.split(" "):
                    if word.lower() in noble_map:
                        ObjectEntitiesID.append(noble_map[word.lower()])
        
        if len(ObjectEntitiesID) == 0:
            ObjectEntitiesID = [""]

        # remove duplicates:
        ObjectEntitiesID = list(set(ObjectEntitiesID))
        clean_result = {
            "SubjectEntityID": row["SubjectEntityID"],
            "SubjectEntity": row["SubjectEntity"],
            "Relation": row["Relation"],
            "ObjectEntitiesSurfaceForms": row["ObjectEntitiesSurfaceForms"], 
            "ObjectEntitiesID": ObjectEntitiesID
        }
        clean_results.append(clean_result)

    clean_file = output.split(".jsonl")[0] + '_clean.jsonl'
    save_df_to_jsonl(Path(clean_file), clean_results)


def run(args):

    input_df = read_lm_kbc_jsonl_to_df(Path(args.input))
    print (input_df.describe())

    if args.restart == 0:
        with open(Path(args.output), "w") as f:
            pass

    if args.restart < len(input_df):
        print("Resuming at: ", args.restart)
        results = probe_LLMS(
            input_df, 
            restart=args.restart,
            output=args.output,
            modified_relation=args.modified_relation,
            model_name=args.model_name
        )
    else:
        results = read_lm_kbc_jsonl(Path(args.output))

    clean_objectID_predictions(results, args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Model with Question and Fill-Mask Prompts")
    parser.add_argument("-i", "--input", type=str, required=True, help="Input (subjects) file")
    parser.add_argument("-o", "--output", type=str, required=True, help="Predictions (output) file")
    parser.add_argument("-k", "--oaikey", type=str, required=True, help="OpenAI API key")
    parser.add_argument("-r", "--restart", type=int, default=0, help="Index to restart probing")
    parser.add_argument("-m", "--modified_relation", choices=[0,1], default=0, help="To use (1) or not use (0) modified relations")
    parser.add_argument("-d", "--disambiguate", choices=[0,1], default=0, help="To use baseline (0) or search (1) disambiguation")
    parser.add_argument("-llm", "--model_name", choices=["gpt-4", "gpt-3.5-turbo"], default="gpt-3.5-turbo", help="OpenAI model name")
    #parser.add_argument("-f", "--few_shot", type=int, default=5, help="Number of few-shot examples (default: 5)")
    #parser.add_argument("--train_data", type=str, required=True, help="CSV file containing train data for few-shot examples (required)")

    args = parser.parse_args()

    run(args)