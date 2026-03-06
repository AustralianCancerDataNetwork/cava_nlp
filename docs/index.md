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

