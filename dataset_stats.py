"""
Return certain dataset characteristics given train/val files.

#relations
#objects per relation
#WD-linked objects
#empty objects
"""
import json
import argparse


def read_jsonl(filename):
	data = []
	with open(filename, "r") as fp:
		for line in fp:
			data.append(json.loads(line))
	return data

def dataset_stats(args):
	data = {}
	data["train"] = read_jsonl(args.train)
	data["val"] = read_jsonl(args.val)
	if args.predict is not None:
		data["predict"] = read_jsonl(args.predict)
	stats = {}
	for split in data:
		stats[split] = {}
		for record in data[split]:
			if record["Relation"] not in stats[split]:
				stats[split][record["Relation"]] = {"num_ObjectEntities": [], "num_ObjectEntitiesID": []}
			if "NumberOf" in record["Relation"] and record["ObjectEntities"] == ["0"]:
				stats[split][record["Relation"]]["num_ObjectEntities"].append(0)
				stats[split][record["Relation"]]["num_ObjectEntitiesID"].append(0)
			elif record["ObjectEntities"] != [""]:
				stats[split][record["Relation"]]["num_ObjectEntities"].append(len(record["ObjectEntities"]))
				stats[split][record["Relation"]]["num_ObjectEntitiesID"].append(len(record["ObjectEntitiesID"]))
			else:
				stats[split][record["Relation"]]["num_ObjectEntities"].append(0)
				stats[split][record["Relation"]]["num_ObjectEntitiesID"].append(0)
		print("===========%s==========="%split)
		print("Relations              : ", len(data[split]))
		print("%30s%20s%20s%20s%20s"%("Relation", "Num Subjects", "Avg. Obj entities", "Avg. Obj entity IDs", "#Zero objects"))
		for relation in stats[split]:
			num_subjects = len(stats[split][relation]["num_ObjectEntities"])
			avg_entities = sum(stats[split][relation]["num_ObjectEntities"])/len(stats[split][relation]["num_ObjectEntities"])
			avg_entity_ids = sum(stats[split][relation]["num_ObjectEntitiesID"])/len(stats[split][relation]["num_ObjectEntitiesID"])
			num_zero_objects = stats[split][relation]["num_ObjectEntities"].count(0)
			print("%30s%20d%20.3f%20.3f%20d"%(relation, num_subjects, avg_entities, avg_entity_ids, num_zero_objects))

if __name__ == "__main__":
	parser = argparse.ArgumentParser("Give descriptive stats about the dataset")
	parser.add_argument("-t", "--train", required=True, type=str, help="Train file in jsonl format.")
	parser.add_argument("-v", "--val", required=True, type=str, help="Validation file in jsonl format.")
	parser.add_argument("-p", "--predict", type=str, default=None, help="Prediction file on test set in jsonl format (optional).")

	args = parser.parse_args()

	dataset_stats(args)