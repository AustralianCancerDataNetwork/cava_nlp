# Getting started

## Install

```bash
pip install cava_nlp
```

### Create an NLP pipeline

```python
from cava_nlp.language import CaVaLang
n = CaVaLang()
n.add_pipe("clinical_normalizer", first=True)
n.add_pipe("rule_engine", name="ecog_value", config={...})
doc = n("The patient's ECOG score is 2.")
for ent in doc.ents:
    print(ent.text, ent.label_, ent._.normalisation)
```