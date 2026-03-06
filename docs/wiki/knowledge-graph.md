# Knowledge Graphs

This page explains the transition from traditional relational data storage to **Knowledge Graphs (KG)** and how we implement them via **Virtual Knowledge Graphs (VKG)** using [`omop-graph`](components.md#omop-graph).

## 1. What is a Knowledge Graph?
A dataset becomes a **Knowledge Graph** when it moves beyond simple records and satisfies three core properties:

* **Entities are Nodes:** Nodes represent real conceptual things (e.g., "Type 2 Diabetes Mellitus"), not just database records.
* **Relationships have Semantic Meaning:** Edges represent typed relationships (e.g., `Metformin --treats--> Diabetes`) rather than technical joins.
* **Navigable Graph:** Edges compose to support reasoning and context, such as tracing a path from a drug to its therapeutic use.


## 2. Relational Joins vs. Semantic Edges
A **relational join** is a technical link between tables, but it is not necessarily a **semantic relationship**. In a KG, every edge must mean something in the real world.

| Feature | Relational Database (SQL) | Knowledge Graph (Semantic) |
| :--- | :--- | :--- |
| **Basic Unit** | Record / Row  | Entity / Node  |
| **Links** | Primary/Foreign Key Joins | Typed Semantic Edges |
| **Goal** | Data Storage | Reasoning & Context |

## 3. OMOP as a "Mixed Graph"
The OMOP vocabulary tables (`concept`, `concept_relationship`, `concept_ancestor`) are structurally a graph schema. However, OMOP is a "mixed graph" because not every relationship encodes clinical knowledge - some are purely for ETL or historical metadata.

To create a clean graph, we must categorize these relationships:

| Category (PredicateKind) | Use for VKG | Functional Description | OMOP Relationship Examples |
| :--- | :--- | :--- | :--- |
| **ONTO_UP / ONTO_DOWN** | **Yes** | Hierarchical taxonomy and subsumption (Parent/Child). **Hierarchical (vertical) connection** | `Is a`, `Subsumes` |
| **MAPS_TO / MAPS_FROM** | **Yes** | Cross-vocabulary equivalence and identity mapping. **Associative (horizontal) connection** | `Maps to`, `RxNorm - Source eq`, `same_as` |
| **COMPOSITION** | **Yes** | Structural parts, active ingredients, and components. | `Has ingredient`, `Part of`, `Contains` |
| **INTERACTION** | **Yes** | Clinical logic: treatments, causes, and contraindications. | `Treats`, `Contraindicated in`, `Induces` |
| **ATTRIBUTE** | Optional | Quantitative or qualitative properties of a concept. | `Has unit`, `Has dose form`, `Has value` |
| **VERSIONING** | No | Lifecycle metadata and concept history. | `Concept replaced by`, `Invalid`, `Was a` |
| **METADATA** | No | Temporal, physiological, or process-oriented descriptors. | `Occurs during`, `Associated with`, `Used by` |



## 4. Virtual Knowledge Graphs (VKG)
A **Virtual Knowledge Graph** allows us to treat our relational OMOP database as a graph without moving the data into a specialized graph database (inspired by [Ontop](https://ontop-vkg.org/)).

### Implementation Strategy
We avoid modifying the CDM directly. Instead, we use a **Semantic Layer** (a helper classification table) to filter the edges that represent actual knowledge.

```sql
/* Querying the VKG for a clean semantic layer */
SELECT r.*
FROM concept_relationship r
JOIN relationship_semantics s ON r.relationship_id = s.relationship_id
WHERE s.include_in_vkg = true;
```

## 5. Importance for LLM Grounding
