# Welcome to the CaVa Onboarding Wiki

This documentation serves as the "How to get started" guide for new team members joining the **CaVa** project. Here, you will find the essential architectural concepts, technical anchor points, and workflow definitions required to work with clinical data and the **spaCy** ecosystem.

## General Mission
The CaVa platform is designed to ingest raw clinical data (specifically oncology), process it through an automated pipeline, and provide anonymized, structured data to researchers. By transforming clinical narratives into a verifiable format, we ensure that the resulting research is grounded, reproducible, and valid. As such, it constitutes the **ETL (Extract, Transform, Load) pipeline** for research at UNSW.

## Core Design Philosophy
The entire pipeline is built on two pillars: **Reproducibility** and **Shareability**. These principles dictate how we build our components:

* **Registry-Based Methods:** We define functions using [spaCy registries](https://spacy.io/usage/training#custom-functions). This allows us to use configuration files (`config.cfg`) to define entire pipelines. 
* **Configuration over Code:** By sharing a config file, different researchers can "plug in" the exact same pipeline logic to their local environments, ensuring identical results across institutions.
* **Standardized Mapping:** We use global ontologies to ensure that a "migraine" in one hospital and a "vascular headache" in another are mapped to the exact same unique identifier.

## How to navigate this Wiki
1.  **[OMOP & Athena](omop.md):** Understand the data models and vocabularies that form our foundation.
2.  **[Knowledge Graphs](knowledge-graph.md):** Information of knowledge graphs, graph traversal & reasoning, and knowledge extraction
3.  **[System Components](components.md):** An overview of the specific software packages developed for the CaVa ecosystem.
4.  **[Inference & Grounding](inference-grounding.md):** How we use NLP and LLMs to bridge the gap between raw text and structured logic.