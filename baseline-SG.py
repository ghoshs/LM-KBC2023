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

def set_prefix(n_example, relation, modified_relation):
    examples = {
        "BandHasMember":  {"SubjectEntityID": "Q125603", "SubjectEntity": "The Clash", "ObjectEntitiesID": ["Q310052", "Q357310", "Q449804", "Q466088", "Q540440", "Q1389464"], "ObjectEntities": ["Joe Strummer", "Mick Jones", "Paul Simonon", "Terry Chimes", "Topper Headon", "Keith Levene"], "Relation": "BandHasMember"},
        "CityLocatedAtRiver": {"SubjectEntityID": "Q2079", "SubjectEntity": "Leipzig", "ObjectEntitiesID": ["Q162993", "Q44729"], "ObjectEntities": ["Plei\u00dfe", "Weisse Elster"], "Relation": "CityLocatedAtRiver"},
        "CompanyHasParentOrganisation": {"SubjectEntityID": "Q35886", "SubjectEntity": "Lamborghini", "ObjectEntitiesID": ["Q23317"], "ObjectEntities": ["Audi"], "Relation": "CompanyHasParentOrganisation"},
        "CompoundHasParts": {"SubjectEntityID": "Q43656", "SubjectEntity": "Cholesterol", "ObjectEntitiesID": ["Q623", "Q629", "Q556"], "ObjectEntities": ["carbon", "oxygen", "hydrogen"], "Relation": "CompoundHasParts"},
        "CountryBordersCountry": {"SubjectEntityID": "Q30", "SubjectEntity": "United States of America", "ObjectEntitiesID": ["Q16", "Q96"], "ObjectEntities": ["Canada", "Mexico"], "Relation": "CountryBordersCountry"},
        "CountryHasOfficialLanguage": {"SubjectEntityID": "Q213", "SubjectEntity": "Czech Republic", "ObjectEntitiesID": ["Q9056"], "ObjectEntities": ["Czech"], "Relation": "CountryHasOfficialLanguage"},
        "CountryHasStates": {"SubjectEntityID": "Q977", "SubjectEntity": "Djibouti", "ObjectEntitiesID": ["Q283979", "Q645896", "Q705941", "Q821008", "Q844929", "Q12182414"], "ObjectEntities": ["Dikhil Region", "Tadjourah Region", "Arta Region", "Ali Sabieh Region", "Obock Region", "Djibouti Region"], "Relation": "CountryHasStates"},
        "FootballerPlaysPosition": {"SubjectEntityID": "Q185572", "SubjectEntity": "Mikel Arteta", "ObjectEntitiesID": ["Q193592"], "ObjectEntities": ["midfielder"], "Relation": "FootballerPlaysPosition"},
        "PersonCauseOfDeath": {"SubjectEntityID": "Q27214", "SubjectEntity": "Jerry Springer", "ObjectEntitiesID": ["Q212961"], "ObjectEntities": ["pancreatic cancer"], "Relation": "PersonCauseOfDeath"},
        "PersonHasAutobiography": {"SubjectEntityID": "Q11666", "SubjectEntity": "Maria Sharapova", "ObjectEntitiesID": ["Q55663964"], "ObjectEntities": ["Unstoppable"], "Relation": "PersonHasAutobiography"},
        "PersonHasEmployer": {"SubjectEntityID": "Q2642925", "SubjectEntity": "Alexander S. Kekul\u00e9", "ObjectEntitiesID": ["Q153978", "Q310207", "Q32120"], "ObjectEntities": ["University of T\u00fcbingen", "McKinsey & Company", "University of Halle-Wittenberg"], "Relation": "PersonHasEmployer"},
        "PersonHasNoblePrize": {"SubjectEntityID": "Q106547", "SubjectEntity": "Paul Lauterbur", "ObjectEntitiesID": ["Q80061"], "ObjectEntities": ["Nobel Prize in Physiology or Medicine"], "Relation": "PersonHasNoblePrize"},
        "PersonHasNumberOfChildren": {"SubjectEntityID": "Q497827", "SubjectEntity": "Sam Walton", "ObjectEntitiesID": ["4"], "ObjectEntities": ["4"], "Relation": "PersonHasNumberOfChildren"},
        "PersonHasPlaceOfDeath": {"SubjectEntityID": "Q497827", "SubjectEntity": "Sam Walton", "ObjectEntitiesID": ["4"], "ObjectEntities": ["4"], "Relation": "PersonHasNumberOfChildren"},
        "PersonHasProfession": {"SubjectEntityID": "Q109677980", "SubjectEntity": "Roman Izyaev", "ObjectEntitiesID": ["Q28389", "Q1797162", "Q2259451", "Q3387717"], "ObjectEntities": ["screenwriter", "artistic director", "stage actor", "theatrical director"], "Relation": "PersonHasProfession"},
        "PersonHasSpouse": {"SubjectEntityID": "Q20142304", "SubjectEntity": "Camila Queiroz", "ObjectEntitiesID": ["Q951565"], "ObjectEntities": ["Klebber Toledo"], "Relation": "PersonHasSpouse"},
        "PersonPlaysInstrument": {"SubjectEntityID": "Q15994935", "SubjectEntity": "Emma Blackery", "ObjectEntitiesID": ["Q6607", "Q61285", "Q17172850"], "ObjectEntities": ["guitar", "ukulele", "voice"], "Relation": "PersonPlaysInstrument"},
        "PersonSpeaksLanguage": {"SubjectEntityID": "Q788439", "SubjectEntity": "Em\u0151ke Bagdy", "ObjectEntitiesID": ["Q188", "Q9058", "Q9067"], "ObjectEntities": ["German", "Slovak", "Hungarian"], "Relation": "PersonSpeaksLanguage"},
        "RiverBasinsCountry": {"SubjectEntityID": "Q172089", "SubjectEntity": "Oka", "ObjectEntitiesID": ["Q159"], "ObjectEntities": ["Russia"], "Relation": "RiverBasinsCountry"},
        "SeriesHasNumberOfEpisodes": {"SubjectEntityID": "Q85806507", "SubjectEntity": "The Benza", "ObjectEntitiesID": ["13"], "ObjectEntities": ["13"], "Relation": "SeriesHasNumberOfEpisodes"},
        "StateBordersState": {"SubjectEntityID": "Q321455", "SubjectEntity": "Beja", "ObjectEntitiesID": ["Q5777", "Q5783", "Q81803", "Q95015", "Q244521", "Q274109", "Q274118"], "ObjectEntities": ["Extremadura", "Andalusia", "Badajoz Province", "Province of Huelva", "Faro", "Set\u00fabal", "\u00c9vora"], "Relation": "StateBordersState"}
    }
    if n_example == 0:
        return ""
    else:
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
def GPT3response(q, subject, relation):
    response = openai.ChatCompletion.create(
        # model="gpt-3.5-turbo",
        model="gpt-4",
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


def retry_GPT3response(q, subject, relation, initial_delay=1, curr_retry=0, max_retries=10):
    delay = initial_delay
    errors = tuple([openai.error.ServiceUnavailableError, openai.error.RateLimitError, openai.error.APIError, openai.error.Timeout])
    try:
        response = GPT3response(q, subject, relation)

    except errors as e:
        curr_retry += 1
        if curr_retry > max_retries:
            raise Exception("Max retries %d exceeded."%max_retries)

        delay *= 2 * (1 + random.random())

        time.sleep(delay)
        response = retry_GPT3response(q, subject, relation, delay, curr_retry, max_retries)
    return response
        

def disambiguation_baseline(item):
    try:
        url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={item}&language=en&format=json"
        data = requests.get(url).json()
        # Return the first id (Could upgrade this in the future)
        return data['search'][0]['id']
    except:
        return ""


def disambiguation_search(item):
    try:
        params = {
            "action": "query", 
            "format": "json", 
            "list": "search", 
            "srlimit": 1,
            "srprop": "title",
            "srnamespace": 0,
            "srsearch": item
        }
        url = 'https://www.wikidata.org/w/api.php'
        data = requests.get(url=url, params=params).json()
    except:
        return ""
    try:
        return data['query']['search'][0]['title']
    except:
        return ""


def nl_relation(org_relation, modified_relation):
    relation = re.sub('([A-Z][a-z]+)', r' \1', org_relation).strip().lower()
    relation = relation.split(" ")
    subject_type = relation[0]
    relation = " ".join(relation[1:])
    if modified_relation:
        if relation == "has member":
            relation = "has members"
        if relation == "located at river":
            relation = "is located at river"
        if relation == "has parts" and subject_type == "compound":
            relation = "has elements"
        # if relation == "borders country":
        #     relation = "borders countries"
        # if relation == "has official language":
        #     relation = "has official languages"
        if relation == "has states":
            relation = "has provinces"
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
        if relation == "has spouse":
            relation = "has spouses"
        if relation == "plays instrument":
            relation = "plays instruments"
        # if relation == "speaks language":
        #     relation = "speaks languages"
        # if relation == "basins country":
        #     relation = "has basin countries"
        if relation == "borders state":
            relation = "borders provinces"
    return relation


def probe_LLMS(input_df, restart=0, output=None, modified_relation=None, n_example=None, disambiguate=None, has_context=None):
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

        prefix = set_prefix(n_example, row["Relation"], relation)

        prompt = prefix + task + "(\"" +row["SubjectEntity"] + "\", \"" + relation + "\", [])"
        print("Prompt is \"{}\"".format(prompt))

        response = retry_GPT3response(prompt, row["SubjectEntity"], relation, 0, 4)
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
                if not disambiguate:
                    result["ObjectEntitiesID"].append(disambiguation_baseline(s))
                else:
                    result["ObjectEntitiesID"].append(disambiguation_search(s))

        results.append(result)

        with open(Path(output), "a") as f:
            f.write(json.dumps(result) + "\n")
        # time.sleep(1)
    # save_df_to_jsonl(Path(args.output), results)
    return results

    print('Finished probing GPT_3 ................')


def clean_objectID_predictions(results, output):
    clean_results = []
    for row in results:
        # only keep Wikidata object IDs which are not "N/A" or "unknown" or "anonymous" or "false" or "None" or integer values
        ObjectEntitiesID = []
        if not isinstance(row["ObjectEntitiesID"], list):
            row["ObjectEntitiesID"] = [row["ObjectEntitiesID"]]
        for item in row["ObjectEntitiesID"]:
            if isinstance(item, int):
                ObjectEntitiesID.append(str(item))
            else:
                try:
                    item = int(item)
                except ValueError:
                    if item.startswith("Q") and item not in ["Q929804", "Q24238356", "Q4233718", "Q5432619", "Q543287"]:
                        ObjectEntitiesID.append(str(item))
                    else:
                        ObjectEntitiesID.append("")
                else:
                    ObjectEntitiesID.append(str(item))
        if any([item.startswith("Q") for item in ObjectEntitiesID]):
            # If object == subject then keep object empty
            ObjectEntitiesID = [item for item in ObjectEntitiesID if item not in row["SubjectEntityID"]]
        # remove empty strings
        ObjectEntitiesID = [item for item in ObjectEntitiesID if len(item) > 0]
        if row["Relation"] == "PersonHasNoblePrize" and len(row["ObjectEntitiesSurfaceForms"]) > 0 and len(ObjectEntitiesID) == 0:
            for obj in row["ObjectEntitiesSurfaceForms"]:
                for word in obj.split(" "):
                    if word.lower() in noble_map:
                        ObjectEntitiesID.append(noble_map[word.lower()])
        if len(ObjectEntitiesID) == 0:
            ObjectEntitiesID = [""]
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
            n_example=args.n_example,
            disambiguate=args.disambiguate,
            has_context=args.has_context
        )
    else:
        results = read_lm_kbc_jsonl(Path(args.output))

    # results = clean_surfaceforms_predictions(results, args.output)
    clean_objectID_predictions(results, args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Model with Question and Fill-Mask Prompts")
    parser.add_argument("-i", "--input", type=str, required=True, help="Input (subjects) file")
    parser.add_argument("-o", "--output", type=str, required=True, help="Predictions (output) file")
    parser.add_argument("-k", "--oaikey", type=str, required=True, help="OpenAI API key")
    parser.add_argument("-r", "--restart", type=int, default=0, help="Index to restart probing")
    parser.add_argument("-m", "--modified_relation", type=int, default=0, help="To use (1) or not use (0) modified relations")
    parser.add_argument("-n", "--n_example", type=int, default=0, help="To use no example (0) or 1 example (1) in the prompts.")
    parser.add_argument("-c", "--has_context", type=int, default=0, help="To use (1) or not use (0) relation context")
    parser.add_argument("-d", "--disambiguate", type=int, default=0, help="To use baseline (0) or search (1) disambiguation")
    #parser.add_argument("-f", "--few_shot", type=int, default=5, help="Number of few-shot examples (default: 5)")
    #parser.add_argument("--train_data", type=str, required=True, help="CSV file containing train data for few-shot examples (required)")

    args = parser.parse_args()

    run(args)