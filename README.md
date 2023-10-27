# Minimal Probe
Solution entry to the ISWC 2023 challenge on Knowledge Base Construction from Pre-trained Language Models: [LM-KBC](https://lm-kbc.github.io/challenge2023/).

This work present __Minimal Probe__, which predicts objects provided a subject and relation. Through this challenge, we test the limits of LLMs in zero-shot setting, when it comes to object prediction for the task of knowledge base construction.

1. [Dataset](#dataset)
1. [Key Challenges](#challenges)
1. [Scripts](#scripts)
1. [Resutls](#results)
1. [Citation](#citation)
1. [License](#license)

### Dataset <a name="dataset"></a> 

The (LM-KBC dataset)[https://github.com/lm-kbc/dataset2023] is available on Github. It comprises 21 relations. Each relation has an average of 90 unique subjects in each of its data splits (train/val/test).

### Key Challenges <a name="challenges"></a> 

1. Varying number of objects per subject.
    Distribution of the number of objects is quite varied across relations. The maximum number of objects a subject takes is 20.

2. Zero-object cases.
    There are subject-relation pairs which do not have any valid objects. The challenge does not distinguish between unknown, false and none values.

3. Entity disambiguation.
	Each object entity must be linked to Wikidata entities. Zero-object subject-relation pairs should predict empty values. 

### Scripts <a name="scripts"></a> 

1. Baselines
    - `dataset2023/baseline-GPT3-NED.py`: is the baseline provided in the challenge.
    - `baseline-GPT3x-NED.py` is an update of the GPT3 baseline above, using chat models.
    
To run the models:
    `python BASELINE.py -i dataset2023/data/val.jsonl -o results/val/BASELINE.jsonl -k YOUR_OPENAI_KEY_HERE`

2. `minimal_probe.py` is our solution.

To recreate the test results run:
    `python minimal_probe.py -i dataset2023/data/val.jsonl -o results/val/minimal_probe.jsonl -k YOUR_OPENAI_KEY_HERE`

### Results <a name="results"></a> 


### Citation <a name="citation"></a> 

If you use our work please cite us:

```bibtex
@inproceedings{ghosh2023limits,
    title = "Limits of Zero-shot Probing on Object Prediction",
    author = "Shrestha Ghosh",
    booktitle = "To appear at CUER Workshop Proceedings at ISWC 2023",
    month = nov,
    year = "2023",
    url = "https://lm-kbc.github.io/challenge2023/static/papers/paper_3.pdf"
}
```

Full paper available [here](https://lm-kbc.github.io/challenge2023/static/papers/paper_3.pdf)

### License <a name="license"></a>

Shield: [![CC BY 4.0][cc-by-shield]][cc-by]

This work is licensed under a
[Creative Commons Attribution 4.0 International License][cc-by].


[![CC BY 4.0][cc-by-image]][cc-by]

[cc-by]: http://creativecommons.org/licenses/by/4.0/
[cc-by-image]: https://i.creativecommons.org/l/by/4.0/88x31.png
[cc-by-shield]: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg