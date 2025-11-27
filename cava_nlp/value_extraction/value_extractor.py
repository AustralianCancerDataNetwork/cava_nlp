import spacy, string
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
                                             entity_label=entity_label,
                                             exclusion_patterns=exclusion_patterns)
  
        self.value_label = value_label
        self.norm_label = norm_label
        self.value_patterns = value_patterns # what portion of the token should be pulled out as numeric
        self.norm_patterns = norm_patterns   # if set, the normalised form of the token without numeric portion

        Token.set_extension(value_label, default=-1, force=True)
        
        self.value_matcher = Matcher(vocab)
        self.value_matcher.add(value_label, value_patterns)#, on_match=get_ecog_value)
        self.norm_matcher = None
        if norm_patterns:
            self.norm_matcher = Matcher(vocab)
            self.norm_matcher.add(norm_label, norm_patterns)
        self.punct_translator = str.maketrans('', '', ',()')

    def __call__(self, doc):

        spans, matches = self.get_token_spans(doc)
        self.set_entity(doc, matches)

        with doc.retokenize() as retokenizer:
            for span in spacy.util.filter_spans(spans):
                value_matches = self.value_matcher(span)
                values = [-1]
                for value_id, v_start, v_end in value_matches:
                    val = span[v_start:v_end].text.translate(self.punct_translator)
                    try:
                        values.append(int(val))
                    except:
                        try:
                            values.append(float(val))
                        except:
                            if val.lower() in ['zero', 'o']:
                                values.append(0)
                            #if any([t._.sci_not for t in span[v_start:v_end]]):
                            else:
                                values = [val] # if scientific notation or PGSGA we currently return value as string
                                               # consider adding a callable for score normalisation?
                            
                if self.norm_matcher:
                    norm_matches = self.norm_matcher(span)
                    norm = ''.join([span[n_start:n_end].text for norm_id, n_start, n_end in norm_matches])
                else:
                    norm = span.text.lower()
                retokenizer.merge(span, attrs={"NORM": norm})
                for tok in span:
                    tok._.set(self.token_label, True) 
                    try:
                        tok._.set(self.value_label, max(values))
                    except TypeError:
                        longest_val = sorted(values, key=lambda s: len(str(s)))[-1]
                        tok._.set(self.value_label, longest_val)
#                        tok._.set(self.value_label, ' '.join([str(v) for v in values]))
        return doc
