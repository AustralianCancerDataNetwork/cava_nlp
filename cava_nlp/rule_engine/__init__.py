from spacy.language import Language
from .rule_engine import RuleEngine   # your class

@Language.factory("rule_engine")
def create_rule_engine(nlp, name, config):
    return RuleEngine(nlp, name, config)