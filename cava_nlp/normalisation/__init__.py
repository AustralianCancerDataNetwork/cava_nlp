from spacy.language import Language
from .normaliser import ClinicalNormalizer

@Language.factory("clinical_normalizer")
def create_clinical_normalizer(nlp, name):
    return ClinicalNormalizer(nlp)
