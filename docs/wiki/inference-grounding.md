# Inference and Grounding

!!! warning
    ``omop-spires`` references not fully populated as the Github page is not yet online

Grounding is the process of mapping a raw string from a clinical note to a specific, unique **URI** (Unique Resource Identifier) in an ontology (e.g., `OMOP:4329847`).

## Why Grounding Matters: The "Heart Attack" Problem { #why-grounding-matters data-toc-label="Why Grounding Matters"}
In clinical free-text, a single condition can be described in dozens of ways depending on the clinician or the institution. For example, a patient suffering a myocardial infarction might be documented as:

!!! quote
    * "Patient suffered an **MI**"
    * "History of **Heart Attack**"
    * "Confirmed **STEMI** (ST-Elevation Myocardial Infarction)"
    * "Acute **Myocardial Infarction** of the anterior wall"

Without grounding, a researcher searching for "Heart Attack" would miss all records labeled "MI" or "STEMI." By mapping these to a single **Standard Concept ID**, we ensure the data is searchable, reproducible, and logically linked to broader categories like "Ischemic Heart Disease."

## The Grounding Workflow
1.  **Extraction:** We identify a term using either rule-based matching (spaCy) or LLM-based pattern extraction with `omop-spires`
2.  **Inference:** Using the Logic Layer of the ontology, we determine what that term *is*. (e.g., An ontology knows "Lung Cancer" **IS A** "Respiratory Disease" even if the word "Respiratory" isn't in the text).
3.  **Resolution:** We resolve the term to a globally recognized concept ID.

The entire workflow is realised in `omop-spires` relying on LLM concept extraction.


## OntoGPT and omop-spires
For complex patterns that rigid rules can't catch, we use **OntoGPT**. This tool uses Large Language Models (LLMs) to extract information based on a **LinkML schema**.

* **LinkML as the Contract:** We provide the LLM with a LinkML file. This acts as a "schema contract," forcing the LLM to provide output that matches our Python classes and SQL tables. This prevents "data drift."
* **Contextual Extraction:** Unlike simple keyword matching, the LLM can understand context—distinguishing between a patient having a condition and a patient's family member having it.

### Example LinkML schema for cancer staging extraction {#example-linkml data-toc-label="LinkML example schema"}
```yaml
id: http://w3id.org/ontogpt/staging
name: staging
title: Staging Extraction Template
description: >-
  A template for extracting TNM staging from clinical pathology reports, 
  mapping findings to standardized OMOP concepts.
license: https://creativecommons.org/publicdomain/zero/1.0/
prefixes:
  linkml: https://w3id.org/linkml/
  OMOP: http://w3id.org/ontogpt/OMOP/

default_prefix: OMOP

imports:
  - linkml:types
  - ../base_models/omop_base

classes:
  Document:
    tree_root: true
    attributes:
      cancer_diagnoses:
        range: CancerDiagnosis
        multivalued: true
        description: >-
          One or more specific cancer diagnoses or neoplasms mentioned in the text, 
          along with their associated TNM staging components. Multiple entries may 
          exist if different primary tumors are present, or if both clinical and 
          pathological stages are explicitly documented for the same cancer.

  CancerDiagnosis:
    is_a: OMOPEntity
    id_prefixes: 
     - OMOP
    annotations:
     annotators: omop
     parent_ids: OMOP:441840  # Clinical Finding
     domains: Condition
     vocabs:  SNOMED,ICD10CM,HemOnc
    attributes:
      tumour:
        range: TumourStaging
        description: >-
          Primary tumor (T) stage. Look for depth of invasion through the intestinal wall 
          (submucosa, muscularis propria, serosa).
      lymph_node:
        range: LymphNodeStaging
        description: >-
          Regional lymph node (N) involvement. Look for the number of positive nodes 
          or explicit N codes (e.g., N1, N2b).
      metastasis:
        range: MetastasisStaging
        description: >-
          Distant metastasis (M) status. M1 indicates spread to non-regional organs 
          (liver, lungs, etc.).

  TumourStaging:
    is_a: OMOPEntity
    attributes:
      concept_name:
        range: TumourStagingEnum
    annotations: 
      meaning: concept_id

  LymphNodeStaging:
    is_a: OMOPEntity
    attributes:
      concept_name:
        range: LymphNodeStagingEnum
    annotations: 
      meaning: concept_id

  MetastasisStaging:
    is_a: OMOPEntity
    attributes:
      concept_name:
        range: MetastasisStagingEnum
    annotations: 
      meaning: concept_id

enums:
  TumourStagingEnum:
    permissible_values:
      T0:
        meaning: OMOP:1634213
        description: "No evidence of primary tumor."
      T1:
        meaning: OMOP:1635564
        description: "Tumor invades submucosa."
      T2:
        meaning: OMOP:1635562
        description: "Tumor invades muscularis propria."
      T3:
        meaning: OMOP:1634376
        description: "Tumor invades through the muscularis propria into pericolorectal tissues."
      T4:
        meaning: OMOP:1634654
        description: "Tumor invades the visceral peritoneum or invades/adheres to adjacent organs."
      TX:
        meaning: OMOP:1635682
        description: "Tumour stage is unclear or not mentioned."

  LymphNodeStagingEnum:
    permissible_values:
      N0:
        meaning: OMOP:1633440
        description: "No regional lymph node metastasis."
      N1:
        meaning: OMOP:1634434
        description: "Metastasis in 1-3 regional lymph nodes."
      N2:
        meaning: OMOP:1634119
        description: "Metastasis in 4 or more regional lymph nodes."
      N3:
        meaning: OMOP:1635320
        description: "Metastasis in specific distant regional nodes (site dependent)."
      NX:
        meaning: OMOP:1633885
        description: "Lymph node stage is unclear or not mentioned."

  MetastasisStagingEnum:
    permissible_values:
      M0:
        meaning: OMOP:1635624
        description: "No distant metastasis detected."
      M1:
        meaning: OMOP:1635142
        description: "Distant metastasis present in other organs."
      MX:
        meaning: OMOP:1633547
        description: "Metastasis status not mentioned or indeterminate."
```

#### Main components

- `OMOPEntity`: Reworked `NamedEntity` of [OntoGPT](https://monarch-initiative.github.io/ontogpt/) that has two components
    - `concept_id`: The Concept ID of the concept as stated in the OMOP CDM (e.g. `omop:4038835` for [*Hodgkin's disease (clinical)*](https://athena.ohdsi.org/search-terms/terms/4038835))
    - `concept_name`: The clear name of the concept (e.g. [*Hodgkin's disease (clinical)*](https://athena.ohdsi.org/search-terms/terms/4038835) for `omop:4038835`)
- `meaning` in Enums:
    - Allows direct mapping to known `concept_id` without expensive grounding (graph traversal and reasoning). The `concept_id` of the original extracted entityt is empty and will be replaced with the given one.

!!! success
    As the pipeline is designed to be interoperable with the original OntoGPT knowledge extraction, it is important to declare specific components as a `is_a: OMOPEntity` to make use of the specific grounding mechanism of `omop-spires`.

## Technical Requirements
To run the inference/grounding pipeline, you will need:

* **A Capable LLM:** Preferably self-hosted via **Ollama** for data privacy.
* **A Grounding Database:** A local SQLite file built via Oaklib/Athena.
* **Schema Definitions:** LinkML YAML files that define the structure of the data you wish to extract.

For detailed API documentation, visit the [omop-spires GitHub repository](https://github.com/your-repo/omop-spires).