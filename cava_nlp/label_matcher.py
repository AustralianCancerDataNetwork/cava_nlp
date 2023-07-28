import spacy
from spacy.matcher import Matcher
from spacy.tokens import Token, Span, Doc

def get_widest_match(start, end, matches):
    for _, s, e in matches:
        if s<start<e or s<end<e:
            if e-s > end-start:
                return False
    return True

def is_within(ex_m, match):
    return (ex_m[1] >= match[1] and ex_m[2] <= match[2]) or (ex_m[1] <= match[1] and ex_m[2] >= match[2])
    
class LabelMatcher:
    def __init__(self, 
                 vocab, 
                 token_label, 
                 token_patterns, 
                 merge_ents = True,
                 entity_label="",
                 exclusion_patterns=None):
        self.token_label = token_label
        self.entity_label = entity_label
        self.token_patterns = token_patterns # include patterns that you want for the full token including label and value
        self.label_matcher = Matcher(vocab)
        self.label_matcher.add(token_label, token_patterns)
        self.exclusion_patterns = exclusion_patterns # if set, the normalised form of the token without numeric portion
        self.merge_ents = merge_ents
        self.exclusion_matcher = None

        if exclusion_patterns:
            self.exclusion_matcher = Matcher(vocab)
            self.exclusion_matcher.add('exclude', exclusion_patterns)
        Token.set_extension(token_label, default=False, force=True)


    def set_entity(self, doc, matches):
        for (m_id, start, end) in matches:
            if get_widest_match(start, end, matches):
                if self.entity_label != "":
                    entity = Span(doc, start, end, label=self.entity_label)
                    doc.ents += (entity,)
        
    def get_token_spans(self, doc):
        spans, filtered_matches = [], []
        matches = self.label_matcher(doc) 
        # if we have set an exclusionary token that overlaps with the match, we will filter here 
        # e.g. 'performance status: 1' is valid ecog but want to exclude the strings 
        # 'karnofsky performance status: 1' or 'nodal performance status: 1', which can only be done post-hoc
        excl_match = self.exclusion_matcher(doc) if self.exclusion_matcher else []
        for m in matches:
            if get_widest_match(m[1], m[2], matches):
                excluded = any([is_within(ex, m) for ex in excl_match])
                if not excluded:
                    filtered_matches.append(m)
                    spans.append(doc[m[1]:m[2]])
        return spans, filtered_matches

    def split_token(self, doc, lab):
        with doc.retokenize() as retokenizer:
            spans, _ = self.get_token_spans(doc)
            for span in spacy.util.filter_spans(spans):
                for tok in span:
                    if tok._.__getattr__(lab):
                        retokenizer.split(tok, [v for v in tok.text], heads=[tok]*len(tok.text))
                        
    def unset_token(self, doc, lab):
        spans, _ = self.get_token_spans(doc)
        for span in spacy.util.filter_spans(spans):
            for tok in span:
                try:
                    tok._.set(lab, False)   
                except:
                    ...

    
    def __call__(self, doc):
        
        spans, matches = self.get_token_spans(doc)
        self.set_entity(doc, matches)

        with doc.retokenize() as retokenizer:
            for span in spacy.util.filter_spans(spans):
                for tok in span:
                    tok._.set(self.token_label, True) 
                if self.merge_ents:
                    retokenizer.merge(span)
        return doc



# def add_ecog_ent(matcher, doc, i, matches):
#     # Get the current match and create tuple of entity label, start and end.
#     # Append entity to the doc's entity. (Don't overwrite doc.ents!)
#     match_id, start, end = matches[i]
#     if get_widest_match(start, end, matches):
#         entity = Span(doc, start, end, label="ECOG_STATUS")
#         doc.ents += (entity,)
