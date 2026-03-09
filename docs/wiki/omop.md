# OMOP CDM, Athena, and Vocabularies

!!! warning
    ``omop-spires`` references not fully populated as the Github page is not yet online

!!! tip "Additional Resources"
    As this wiki does not go into the definition of Onotologies, OWL and all these concepts, we provide additional resources for this:

    - [Introducing RDFS & OWL](https://linkeddatatools.com/introducing-rdfs-owl/)
    - [OWL](https://www.w3.org/TR/owl-ref/): The strict language used to define the rules (classes, properties, hierarchy)
    - [RDF](https://www.w3.org/TR/owl-semantics/rdfs.html): One file format used to store the graph data in triple stores (Subject -> Predicate -> Object). 

To make clinical data useful for research, we must move away from local hospital jargon toward a **Common Data Model (CDM)**. We utilize the **OMOP (Observational Medical Outcomes Partnership)** standard given its widespread usage and combination of various vocabularies. The OMOP CDM is described in detail [here](https://ohdsi.github.io/CommonDataModel/index.html), with exact description of components [here](https://ohdsi.github.io/CommonDataModel/cdm54.html). There is also an additional [resource](https://ohdsi.github.io/TheBookOfOhdsi/) detailing the entireity of OHDSI (pronounced like *odyssey*), the organisation behind OMOP.

## The Vocabulary Layer (Dictionary Corpi)
Clinical data is often siloed in disparate standardized lists. To understand raw data from hospitals, labs, and insurance claims, we reference:

- **SNOMED CT:** Clinical findings and anatomy.
- **RxNorm:** Standardized drug names and ingredients.
- **LOINC:** Laboratory results and observations.
- **ICD-10:** Billing and diagnosis codes.
- **HemOnc:** Hematology and Ontology
- ...

The full list of vocabularies can be seen on the [Athena webpage](https://athena.ohdsi.org/vocabulary/list) (**login required**). The entireity of vocabularies without logging in can be downloaded from the [OHDSI Webpages](https://oncology.ohdsi.org/vocabularies/).

---

## Athena: The Lookup Portal
[Athena](https://athena.ohdsi.org/) is the OHDSI search portal that combines these separate "Corpi" into the OMOP CDM.

* **What it does:** It flattens thousands of vocabularies into a single, unified database.
* **The Challenge:** Athena is not always "human-readable." A single search can return thousands of IDs (e.g., separate IDs for every specific packaging size of a drug).
* **Our Role:** CaVa creates a more distinct, reproducible data model that adds a metadata layer. This ensures researchers map to the correct level of the ontology (e.g., the active ingredient rather than the box size). This step is part of the [**grounding**](inference-grounding.md), detailed in a different part of the wiki.

---

## The Database Structure

After downloading the vocabularies from [OHDSI](https://oncology.ohdsi.org/vocabularies/), the files can be ingested into a conventional Postgres Database using the `bootstrap.py` script of `omop-spires`. Detailed documentation of this process can be found [here [MISSING]](missing).

### Essential Resources

!!! info "Essential Resources"

    * **[OMOP CDM v5.4 Specifications](https://ohdsi.github.io/CommonDataModel/cdm54.html):** The definitive guide to the data model structure.
    * **[Full ERD Diagram](https://ohdsi.github.io/CommonDataModel/cdm54erd.html):** A visual representation of how all tables relate to one another.

---

### The Standardized Vocabulary Tables
These tables act as the "Master Dictionary." They do not contain patient data; instead, they define medical concepts, their hierarchies, and how different coding systems (like SNOMED and ICD-10) map to one another.

| Table Name | Description | Key Role in CaVa |
| :--- | :--- | :--- |
| **CONCEPT** | The central table containing every unique "Concept ID" for drugs, conditions, procedures, etc. | The primary destination for **Grounding**. Every raw string must resolve to a row here. |
| **VOCABULARY** | A list of the various reference sources (e.g., SNOMED, RxNorm, LOINC, ICD10). | Used to filter or identify the origin of a specific concept. |
| **CONCEPT_RELATIONSHIP** | Defines direct links between two concepts using **predicates** (e.g., "Maps to," "Is a," "Subsumes"). | Crucial for mapping non-standard source codes (ICD-10) to OMOP Standard Concepts. |
| **CONCEPT_ANCESTOR** | A computationally optimized table containing the full hierarchy (all parents and all children) of **standard concepts ONLY**. | **Essential for Inference.** Allows you to find all "Lung Cancers" by querying an ancestor ID. |
| **CONCEPT_SYNONYM** | Contains alternative names or labels for a single Concept ID. | Used to power search features and improve the accuracy of NLP token matching. |
| **DRUG_STRENGTH** | Quantitative details of drug products (ingredients, unit of measure, and strength). | Essential for calculating dosages and ingredient-level exposures. |

---

### Standardized Clinical Data Tables
These tables store the actual "Facts" about a patient. They use the Concept IDs from the Vocabulary tables to ensure the data is structured and comparable.

| Table Name | Description |
| :--- | :--- |
| **PERSON** | The central table for patient demographics (Gender, Race, Birth Date). |
| **CONDITION_OCCURRENCE** | Records of diseases, signs, or symptoms (diagnoses). |
| **DRUG_EXPOSURE** | Records of medications captured from prescriptions or pharmacy claims. |
| **MEASUREMENT** | Structured data regarding biological samples, lab tests, and vital signs. |
| **PROCEDURE_OCCURRENCE** | Records of activities performed on a patient, such as surgeries or imaging. |

---

### Metadata and System Tables
These tables provide the context required to understand the origin and versioning of the dataset.

| Table Name | Description |
| :--- | :--- |
| **CDM_SOURCE** | Metadata about the source database and the version of the OMOP CDM used. |
| **METADATA** | General metadata about the ETL process or specific data quality constraints. |
| **LOCATION** | Geographical information about the patients or the healthcare providers. |

### OMOP CDM v5.4 ERD (linked from OHDSI)
![OMOP CDM v5.4 ERD](https://github.com/OHDSI/CommonDataModel/raw/main/rmd/images/erd.jpg)

---

### A Word on Semantic SQL
While the CaVa pipeline has moved away from full Oaklib implementations (see [omop-graph](components.md#omop-graph) for reasoning), the **Semantic SQL** structure is still vital for tools like **OntoGPT** that rely on OWL/RDF logic. As such, this bit serves merely as a reference to understand other database formats but is **deprecated for CaVa**.

| Table | Purpose |
| :--- | :--- |
| **`statements`** | The **Master Table**. Contains every raw "Triple" (Subject-Predicate-Object). |
| **`entailed_edge`** | The **Transitive Closure**. Stores inferred relationships for fast hierarchy traversal. |
| **`has_oio_synonym_statement`** | A flattened view of synonyms for easy text-searching. |
| **`owl_restriction`** | Stores logical constraints (e.g., "A Valve is Part_Of a Heart"). |

#### Common Predicates
Relationships in these knowledge graphs are defined by **Predicates**:
* `rdfs:subClassOf` (IS_A): Constructs the parent/child hierarchy.
* `omop:in_vocabulary`: Identifies the source dictionary.
* `omop:in_domain`: Determines clinical category (Condition, Drug, etc.).
---