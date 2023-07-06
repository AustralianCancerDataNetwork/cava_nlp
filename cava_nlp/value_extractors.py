
from spacy.language import Language

from .value_extractor import ValueExtractor
from .label_matcher import LabelMatcher

from ._value_extractors import weight_patterns, pgsga_patterns, pgsga_val_patterns, feeding_tube_patterns, \
                               unit_exclusion_patterns, unit_norm_patterns, unit_patterns, unit_val_patterns, \
                               ecog_patterns, ecog_val_patterns, ecog_exclusion

# rule-based matcher for extracting ecog status
@Language.factory("ecog_status")
def create_ecog_status(nlp, name):
    return ECOGStatus(nlp.vocab)

@Language.factory("unit_value")
def create_unit_value(nlp, name):
    return UnitValue(nlp.vocab)

@Language.factory("weight_value")
def create_weight_value(nlp, name):
    return WeightValue(nlp.vocab)

@Language.factory("pgsga_value")
def create_pgsga_value(nlp, name):
    return PGSGAValue(nlp.vocab)

@Language.factory("feeding_tube_value")
def create_feeding_tube(nlp, name):
    return FeedingTube(nlp.vocab)


class WeightValue(LabelMatcher):
    def __init__(self, vocab, *args, **kwargs):
        
        super(WeightValue, self).__init__(vocab=vocab, 
                                          token_label='weight', 
                                          token_patterns=weight_patterns, 
                                          entity_label='weight',
                                          merge_ents=False)
                     

class PGSGAValue(ValueExtractor):
    def __init__(self, vocab, *args, **kwargs):

        super(PGSGAValue, self).__init__(vocab=vocab, 
                                          token_label='pgsga', 
                                          value_label='pgsga_value', 
                                          token_patterns=pgsga_patterns, 
                                          value_patterns=pgsga_val_patterns)


class FeedingTube(LabelMatcher):
    def __init__(self, vocab, *args, **kwargs):
        
        super(FeedingTube, self).__init__(vocab=vocab, 
                                          token_label='feeding_tube', 
                                          token_patterns=feeding_tube_patterns, 
                                          entity_label='feeding_tube')


class UnitValue(ValueExtractor):
    def __init__(self, vocab, *args, **kwargs):

        super(UnitValue, self).__init__(vocab=vocab, 
                                        token_label='unit', 
                                        value_label='unit_value', 
                                        token_patterns=unit_patterns, 
                                        value_patterns=unit_val_patterns,
                                        norm_patterns=unit_norm_patterns,
                                        exclusion_patterns=unit_exclusion_patterns,
                                        norm_label='unit_norm')


class ECOGStatus(ValueExtractor):
    def __init__(self, vocab, *args, **kwargs):

        super(ECOGStatus, self).__init__(vocab=vocab, 
                                         token_label='ecog_status', 
                                         value_label='ecog_status_value', 
                                         token_patterns=ecog_patterns, 
                                         value_patterns=ecog_val_patterns, 
                                         entity_label='ECOG_STATUS',
                                         exclusion_patterns=[ecog_exclusion])

    def __call__(self, doc):
        # This method is invoked when the component is called on a Doc

        # Because of special cases such as ecog 1/2, which will match the 2nd token as a date
        # value, we have to force split and unset any dates within the matched ecog status        
        self.split_token(doc, 'date')
        self.unset_token(doc, 'date')    
        self.split_token(doc, 'decimal')
        self.unset_token(doc, 'decimal')

        return super(ECOGStatus, self).__call__(doc)
