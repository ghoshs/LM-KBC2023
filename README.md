# Minimal Probe
Solution entry to the ISWC 2023 challenge on Knowledge Base Construction from Pre-trained Language Models: (LM-KBC)[https://lm-kbc.github.io/challenge2023/].

This work present __Minimal Probe__, which predicts objects provided a subject and relation. Through this challenge, we test the limits of LLMs in zero-shot setting, when it comes to object prediction for the task of knowledge base construction.

- `baseline-SG.py` is our Minimal Probe. 

### Dataset

The (LM-KBC dataset)[https://github.com/lm-kbc/dataset2023] is available on Github. It comprises 21 relations. Each relation has an average of 90 unique subjects in each of its data splits (train/val/test).

### Key Challenges

1. Varying number of objects per subject.
    Distribution of the number of objects is quite varied across relations. The maximum number of objects a subject takes is 20.

2. Zero-object cases.
    There are subject-relation pairs which do not have any valid objects. The challenge does not distinguish between unknown, false and none values.

3. Entity disambiguation.
	Each object entity must be linked to Wikidata entities. Zero-object subject-relation pairs should predict empty values. 

### Script

`baseline-GPT3x-NED.py` is an update of the GPT3 baseline provided in the challenge, using chat models.
