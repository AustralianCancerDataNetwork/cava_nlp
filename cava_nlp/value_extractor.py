import spacy
from spacy.matcher import Matcher
from spacy.tokens import Token, Span, Doc

from .label_matcher import LabelMatcher

class ValueExtractor(LabelMatcher):
    def __init__(self, 
                 vocab, 
                 token_label, 
                 value_label, 
                 token_patterns, 
                 value_patterns, 
                 entity_label="",
                 norm_label="", 
                 norm_patterns=None,
                 exclusion_patterns=None):

        super(ValueExtractor, self).__init__(vocab=vocab, 
                                             token_label=token_label, 
                                             token_patterns=token_patterns, 
                                             entity_label=entity_label)
  
        self.value_label = value_label
        self.norm_label = norm_label
        self.value_patterns = value_patterns # what portion of the token should be pulled out as numeric
        self.norm_patterns = norm_patterns   # if set, the normalised form of the token without numeric portion
        self.exclusion_patterns = exclusion_patterns   # if set, the normalised form of the token without numeric portion

        Token.set_extension(value_label, default=-1, force=True)
        
        self.value_matcher = Matcher(vocab)
        self.value_matcher.add(value_label, value_patterns)#, on_match=get_ecog_value)
        self.norm_matcher = None
        self.exclusion_matcher = None
        if norm_patterns:
            self.norm_matcher = Matcher(vocab)
            self.norm_matcher.add(norm_label, norm_patterns)
        if exclusion_patterns:
            self.exclusion_matcher = Matcher(vocab)
            self.exclusion_matcher.add('exclude', exclusion_patterns)

    def __call__(self, doc):

        spans, matches = self.get_token_spans(doc)
        self.set_entity(doc, matches)

        with doc.retokenize() as retokenizer:
            for span in spacy.util.filter_spans(spans):
                value_matches = self.value_matcher(span)
                values = [-1]
                for value_id, v_start, v_end in value_matches:
                    try:
                        values.append(int(span[v_start:v_end].text.replace(',', '')))
                    except:
                        try:
                            values.append(float(span[v_start:v_end].text.replace(',', '')))
                        except:
                            if span[v_start:v_end].text.lower() in ['zero', 'o']:
                                values.append(0)
                            #if any([t._.sci_not for t in span[v_start:v_end]]):
                            else:
                                values = [span[v_start:v_end].text] # if scientific notation we currently return value as string
                            
                if self.norm_matcher:
                    norm_matches = self.norm_matcher(span)
                    norm = ''.join([span[n_start:n_end].text for norm_id, n_start, n_end in norm_matches])
                else:
                    norm = span.text.lower()
                retokenizer.merge(span, attrs={"NORM": norm})
                for tok in span:
                    tok._.set(self.token_label, True) 
                    tok._.set(self.value_label, max(values))
        return doc
