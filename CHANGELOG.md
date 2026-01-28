# version history:
## 0.1.1 
- cava lang alpha = 0.1.0
## 0.2.0
- upgraded alpha to work with python 3.10 = 0.2.0
## 0.3.0
- upgraded alpha to work with poetry & python 3.11 = 0.3.0
## 0.8.0 
- major refactor utilising rule_engine, namespaces
- new test cases
- normalisation module pulled into its own space
- released cava lang beta 0.8
- note that this is stuck on python 3.11 due to pysbd escape issue PEP701 also changed to uv versions for dependencies
## 0.8.1
- loosenend strprtf version requirements for compatibility
## 0.8.2
- added custom context handlers back in
## 0.8.3
- bugfix for overly enthusiastic removal of unused imports
## 0.8.4
- bugfix for overwriting medspacy context defaults
## 0.8.5
- additional bugfix for overwriting medspacy context defaults
## 0.8.6
- new context resolution step - intended for lab results
- modification to handle context profiles
## 0.8.7
- modified package data resource paths 
## 0.9.0
- refactoring of rule engine to validate configuration on load
- typing considerations
- initial docs
## 0.9.1
- stripped punctuation at start/end of rule-engine matches