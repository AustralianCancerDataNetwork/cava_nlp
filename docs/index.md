# cava_nlp

`cava_nlp` is a **spaCy pipeline** designed for real-world clinical text, with
a specific focus on cancer-specific text: pathology reports, progress notes, 
registry extracts, and free-text fields shaped by clinical workflows rather than linguistic norms.

It prioritises:

- notation-heavy (e.g. `mg/kg`, `10^9`, `ECOG 1`)
- inconsistently spaced or punctuated
- rich in abbreviations and symbols
- structured meaning across critical token types (e.g. dates, dosages, measurements)

---


## 1. Create a CaVa pipeline

`cava_nlp` pipelines are constructed explicitly and do not rely on pretrained language models.

```python
from cava_nlp import CaVaLang

nlp = CaVaLang()
```

Out of the box, this provides:

- deterministic clinical tokenisation
- whitespace normalisation
- email masking prior to tokenisation
- medSpaCy sentence splitting

```python
doc = nlp("Email me at test@example.com")

doc.text
# "Email me at xxxxxxxxxxxxxxx"
```

The original structure of the text is preserved while protecting
tokenisation and downstream rules from incidental artefacts.

---

## 2. Add clinical normalisation

Clinical text often expresses structured meaning across multiple tokens
(e.g. decimals, dates, units).  
The clinical normaliser merges these spans and assigns canonical forms.

```python
nlp.add_pipe("clinical_normalizer", first=True)

doc = nlp("Temp is 36.9 today")
```

Inspecting tokens:

```python
for t in doc:
    print(t.text, t.norm_, t._.kind, t._.value)
```

Example output:

```python
Temp Temp None None
is is None None
36.9 36.9 decimal 36.9
today today None None
```

Key points:

- spans may be merged into single tokens
- `token.norm_` provides the canonical representation
- structured values are stored on token extensions
- the original text remains intact

---

## 3. Normalisation produces span groups

Normalised tokens are grouped automatically:

```python
doc.spans.keys()
# dict_keys(['decimal', 'date', 'time', 'unit_norm', ...])
```

These span groups allow downstream components to reason over
normalised clinical concepts without re-parsing raw text.

---

## 4. Add a rule engine

Rule engines layer domain-specific meaning on top of normalisation.
Each engine is added independently.

```python
nlp.add_pipe(
    "rule_engine",
    name="ecog_value",
    config={
        "engine_config_path": None,
        "component_name": "ecog_status",
    },
)
```

Processing text:

```python
doc = nlp("ECOG 1")
```

Results:

```python
[(ent.text, ent.label_) for ent in doc.ents]
# [('ECOG 1', 'ecog_status')]```

Structured values are available via span attributes:

```python
doc.spans["ecog_status"][0]._.value
# 1
```

Rule engines support:

- value extraction and aggregation
- exclusions and fallbacks
- literal or computed assignments
- emission of both entities and span groups

---

## Relevant contributions

1. **Tokenisation**  
   Clinical-oriented, deterministic, and explicit.

2. **Normalisation**  
   Merge spans, assign canonical forms, attach structure.

3. **Rule engines**  
   Map patterns to domain meaning and values based on configuration definitions.


