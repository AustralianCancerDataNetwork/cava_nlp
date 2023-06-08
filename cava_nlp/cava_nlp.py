import spacy, re
from spacy.lang.en import English
from spacy.symbols import ORTH, NORM
from striprtf.striprtf import rtf_to_text
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokenizer import Tokenizer
from spacy.tokens import Token, Span, Doc
from spacy.lang.en import English, TOKENIZER_EXCEPTIONS

from .tokenizer_exceptions import special_cases, units_regex, unit_suffix, months, ordinal, \
                                  times, abbv, no_whitespace, emails, day_regex, year_regex, \
                                  numeric_month_regex, scientific_notation, weight_units

# retokeniser that allows us to tokenise brutally in the first step (e.g. all slashes, all periods, all commas)
# and then reassemble important tokens that shouldn't be broken up such as decimal numbers, units that don't
# fit the basic num/denum form e.g. 10mg/20mL or slashes with no whitespace and alpha characters on both sides
# e.g. O/E or known tumor markers 

@Language.factory("cava_retokenizer")
def create_cava_retokenizer(nlp, name):
    return CaVaRetokenizer(nlp)

@spacy.registry.tokenizers("cava.Tokenizer.v1")
def create_tokenizer():

    def tokenizer_factory(nlp):
        return CaVaRetokenizer(nlp)#.vocab,
                            #    rules = nlp.Defaults.tokenizer_exceptions,
                            #    prefix_search = prefix_search,
                            #    suffix_search = suffix_search,
                            #    infix_finditer = infix_finditer, 
                            #    token_match = nlp.Defaults.token_match,
                            #    url_match = nlp.Defaults.url_match)

    return tokenizer_factory

class CaVaMatcher(Matcher):

    def __init__(self, *args, **kwargs):
        super(CaVaMatcher, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return super(CaVaMatcher, self).__call__(*args, **kwargs)


class CaVaRetokenizer(Tokenizer):

    def __init__(self, nlp): # vocab, rules, prefix_search, suffix_search, 
                             # infix_finditer, token_match, url_match):
        prefixes = nlp.Defaults.prefixes
        suffixes = nlp.Defaults.suffixes
        infixes = nlp.Defaults.infixes

        prefix_search = spacy.util.compile_prefix_regex(prefixes).search if prefixes else None
        suffix_search = spacy.util.compile_suffix_regex(suffixes).search if suffixes else None
        infix_finditer = spacy.util.compile_infix_regex(infixes).finditer if infixes else None
        
        super(CaVaRetokenizer, self).__init__(nlp.vocab, nlp.Defaults.tokenizer_exceptions, 
                                              prefix_search, suffix_search, 
                                              infix_finditer, nlp.Defaults.token_match, 
                                              nlp.Defaults.url_match)

        sci_notation_patterns = [[{"LOWER":"x", "OP": "?"},
                                  {"TEXT": "10"}, 
                                  {"LOWER":"x", "OP": "?"},
                                  {"TEXT": {"IN":["^", "**"]}},
                                  {"IS_DIGIT": True}],
                                  [{"IS_DIGIT": True},
                                   {"LOWER": "e"},
                                   {"TEXT": "+", "OP": "?"},
                                   {"IS_DIGIT": True}]
                                ]

        decimal_patterns = [[{"IS_DIGIT": True, "LIKE_NUM": True}, 
                             {"ORTH": {"IN": ['.', ',']}, 'SPACY': False}, 
                             {"IS_DIGIT": True, "LIKE_NUM": True}]]

        date_patterns = [[{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "-", "SPACY": False}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20 - keep as digit based because 3 part unlikely to be false pos 
                         [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "-", "SPACY": False}, {"IS_DIGIT": True}, {"IS_DIGIT": True}, {"ORTH": ":", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": ":", "SPACY": False}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20 with times HH:MM:SS
                         [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "/", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "/", "SPACY": False}, {"IS_DIGIT": True}], # no longer expressed as 'in', as we really want the separators to be the same
                         [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": ".", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": ".", "SPACY": False}, {"IS_DIGIT": True}], 
                         [{"TEXT": {"REGEX": numeric_month_regex}, 'SPACY': False},  {"ORTH": {"IN": ["/", "-"]}, 'SPACY': False}, {"TEXT": {"REGEX": year_regex}}], # 1/2020, 1-2020 - changed from is digit to avoid false pos with BP
                         [{"TEXT": {"REGEX": day_regex}, 'SPACY': False},  {"ORTH": {"IN": ["/", "-"]}, 'SPACY': False}, {"TEXT": {"REGEX": numeric_month_regex}}], # 31/12
                         [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "/", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": "/", "SPACY": False}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # 1-Jan-20, 1/jan/20
                         [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": "-", "SPACY": False}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # no longer expressed as 'in', as we really want the separators to be the same
                         [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": ".", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": ".", "SPACY": False}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], 
                         [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": numeric_month_regex}}, {"TEXT": {"REGEX": ordinal}}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # September 4th
                         [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": year_regex}}], # Jan/2020, Jan 2020, Jan '20
                         [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": numeric_month_regex}}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}]] # September 4th

        dp = [[],[]] # dates must either start sentence or have preceding space, to avoid false pos with spinal notation e.g. C3/4
        for d in date_patterns:
            dp[0].append([{"SPACY": True}] + d)
            dp[0].append([{"TEXT": {"IN": ["\n", "\n\n"]}}] + d)
            sent_start = [attr.copy() for attr in d]
            sent_start[0]["IS_SENT_START"] = True
            dp[1].append(sent_start)

        time_patterns = [[{"ORTH": "@", "OP": "?"}, 
                          {"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}}, 
                          {"IS_DIGIT": True}, {"LOWER": {"IN": times}}],
                          [{"ORTH": "@", "OP": "?"},  
                          {"IS_DIGIT": True}, {"LOWER": {"IN": times}}],
                          [{"ORTH": "@", "OP": "?"}, {"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}, "SPACY": False}, 
                           {"IS_DIGIT": True, "SPACY": False}, {"ORTH": {"IN": [":", "-", "."]}, "SPACY": False}, 
                           {"IS_DIGIT": True, "SPACY": False}]]

        # making sure we can mark a question mark at the beginning of a word as a query despite it being tokenised
        # e.g. ?query timing
        query_patterns = [[{"TEXT": {"IN": ["?"]}}, {"IS_ALPHA": True}]]

        # these are non-specific merge steps that will re-join alphanumeric tokens split by a slash, 
        # or tokens that appear to be actual acronyms (single chars split by period) p.o, p.o., a.b.v etc.
        other_remerge = [[{"TEXT": {"REGEX": abbv}}, {"ORTH": "/"}, {"TEXT": {"REGEX": abbv}}],
                         [{"TEXT": {"REGEX": abbv}}, {"ORTH": '.', "OP": "?"}, {"IS_DIGIT": True}],
                         [{"TEXT": {"REGEX": abbv}}, {"IS_DIGIT": True}, {"TEXT": {"REGEX": abbv}}, {"IS_DIGIT": True}],
                         [{"TEXT": {"REGEX": abbv}}, {"ORTH": '.'}, {"TEXT": {"REGEX": abbv}}, {"ORTH": '.', "OP": "?"}],
                         [{"TEXT": {"REGEX": abbv}}, {"ORTH": '.'}, {"TEXT": {"REGEX": abbv}}, {"ORTH": '.'}, {"TEXT": {"REGEX": abbv}}, {"ORTH": '.', "OP": "?"}]]
        
        Token.set_extension("sci_not", default=False, force=True)
        Token.set_extension("decimal", default=False, force=True)
        Token.set_extension("date", default=False, force=True)
        Token.set_extension("time", default=False, force=True)

        self.date_matcher_skip = CaVaMatcher(nlp.vocab)
        self.date_matcher = CaVaMatcher(nlp.vocab)
        self.time_matcher = CaVaMatcher(nlp.vocab)
        self.decimal_matcher = CaVaMatcher(nlp.vocab)
        self.query_matcher = CaVaMatcher(nlp.vocab)
        self.sci_not_matcher = CaVaMatcher(nlp.vocab)
        self.other = CaVaMatcher(nlp.vocab)
        
        self.date_matcher_skip.add("date", dp[0])
        self.date_matcher.add("date", dp[1])
        self.sci_not_matcher.add("sci_not", sci_notation_patterns)
        self.decimal_matcher.add("decimal", decimal_patterns)
        self.time_matcher.add("time", time_patterns)
        self.query_matcher.add("query", query_patterns)
        self.other.add("other", other_remerge)

    def set_extension(self, token, name):
        token._.__setattr__(name, True)
        
    def merge_spans(self, matches, doc, name="", skip_first=False):
        spans = []  # Collect the matched spans here
        for match_id, start, end in matches:
            spans.append(doc[start:end])
        # if no named extension, we allow matches only if first token in span does not have 
        # trailing whitespace. this is because the unnamed merges are less specific and 
        # more inclined to create false pos matches
        with doc.retokenize() as retokenizer:
            for span in spacy.util.filter_spans(spans):
                if name == "" and len([s for s in span[:-1] if s.whitespace_]) > 0:
                    continue
                # skipping first token in match for dates only at this point, because we look backwards to check for space
                if skip_first:
                    span = span[1:]
                retokenizer.merge(span)
                if name != "":
                    for token in span:
                        self.set_extension(token, name) 
      
    def mark_queries(self, matches, doc):
        # this gives a question mark at the start of a word with no whitespace in between
        # the norm of 'query', as per '??' and '???', but question marks at the end of a 
        # sentence are left as-is
        for match_id, start, end in matches:
            if doc[start].whitespace_ == '':
                doc[start].norm_ = 'query'
                    
    def __call__(self, doc):
        doc = super(CaVaRetokenizer, self).__call__(doc)
        self.merge_spans(self.date_matcher_skip(doc), doc, 'date', True)
        self.merge_spans(self.date_matcher(doc), doc, 'date')
        self.merge_spans(self.time_matcher(doc), doc, 'time')
        self.merge_spans(self.decimal_matcher(doc), doc, 'decimal')
        self.merge_spans(self.sci_not_matcher(doc), doc, 'sci_not')
        self.mark_queries(self.query_matcher(doc), doc)
        return doc

# # trained NER for extracting oral drugs
# @Language.factory("oral_meds")
# def ..

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


def get_widest_match(start, end, matches):
    for _, s, e in matches:
        if s<start<e or s<end<e:
            if e-s > end-start:
                return False
    return True

def add_ecog_ent(matcher, doc, i, matches):
    # Get the current match and create tuple of entity label, start and end.
    # Append entity to the doc's entity. (Don't overwrite doc.ents!)
    match_id, start, end = matches[i]
    if get_widest_match(start, end, matches):
        entity = Span(doc, start, end, label="ECOG_STATUS")
        doc.ents += (entity,)


def is_within(ex_m, match):
    return (ex_m[1] >= match[1] and ex_m[2] <= match[2]) or (ex_m[1] <= match[1] and ex_m[2] >= match[2])
    

class LabelMatcher:
    def __init__(self, 
                 vocab, 
                 token_label, 
                 token_patterns, 
                 merge_ents = True,
                 entity_label=""):
        self.token_label = token_label
        self.entity_label = entity_label
        self.token_patterns = token_patterns # include patterns that you want for the full token including label and value

        self.label_matcher = Matcher(vocab)
        self.label_matcher.add(token_label, token_patterns)
        self.exclusion_matcher = None
        self.merge_ents = merge_ents

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

        Token.set_extension(value_label, default=-1, force=True )
        
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


class WeightValue(LabelMatcher):
    def __init__(self, vocab, *args, **kwargs):
        
        weight_patterns = [[{"_":{"unit": True}, "NORM": {"IN": weight_units}}]]

        super(WeightValue, self).__init__(vocab=vocab, 
                                          token_label='weight', 
                                          token_patterns=weight_patterns, 
                                          entity_label='weight',
                                          merge_ents=False)
                     

class PGSGAValue(ValueExtractor):
    def __init__(self, vocab, *args, **kwargs):
        
        pgsga_patterns = [[{"LOWER": {"IN": ['pg', 'pgsga']}},
                           {"TEXT": {"IN": ["-", '_']}, "OP": "?"},
                           {"LOWER": "sga", "OP": "?"},
                           {"LOWER": {"IN": ["score", ":", "=", "rating"]}, "OP": "?"},
                           {"IS_DIGIT": True},
                           {"TEXT": "/",  "OP": "?"},
                           {"LOWER": {"IN": ['a', 'b', 'c']}}],
                          [{"LOWER": {"IN": ['pg', 'pgsga']}},
                           {"TEXT": {"IN": ["-", '_']}, "OP": "?"},
                           {"LOWER": "sga", "OP": "?"},
                           {"LOWER": {"IN": ["score", ":", "=", "rating"]}, "OP": "?"},
                           {"LOWER": {"IN": ['a', 'b', 'c']}},
                           {"TEXT": "/",  "OP": "?"},
                           {"IS_DIGIT": True}]] 
                
        
        # to match just the numeric portion within an ECOG status entity
        pgsga_val_patterns = [[{"IS_DIGIT": True},
                               {"TEXT": "/",  "OP": "?"},
                               {"LOWER": {"IN": ['a', 'b', 'c']}}],
                              [{"LOWER": {"IN": ['a', 'b', 'c']}},
                               {"TEXT": "/",  "OP": "?"},
                               {"IS_DIGIT": True}]]

        super(PGSGAValue, self).__init__(vocab=vocab, 
                                          token_label='pgsga', 
                                          value_label='pgsga_value', 
                                          token_patterns=pgsga_patterns, 
                                          value_patterns=pgsga_val_patterns)


class FeedingTube(LabelMatcher):
    def __init__(self, vocab, *args, **kwargs):
        
        feeding_tube_patterns = [[{'LOWER': 'g'}, {'TEXT': '-', 'OP': '?'}, {'LOWER': 'tube'}],
                                 [{"LOWER": {"IN": ['i', 'r']}},
                                  {"LOWER": {"IN": ['/']}},
                                  {"LOWER": {"IN": ['o']}},
                                  {"LOWER": {"IN": ['peg', 'ngt', 'rig', 'pej']}}],
                                 [{"LOWER": {"IN": ['peg', 'ngt', 'rig', 'pej']}}],
                                 [{"LOWER": {"FUZZY2": 'nasogastric'}}, {'LOWER': 'tube', "OP": "?"}],
                                 [{"LOWER": {"FUZZY2": {'IN': ['radiological', 'percutaneous', 'balloon', 'surgical']}}, "OP": '?'},
                                  {"LOWER": {"FUZZY2": {'IN': ['inserted', 'endoscopic']}}, "OP": '?'},
                                  {"LOWER": {"FUZZY2": {'IN': ['gastrostomy', 'jejunostomy']}}}]] 
                
        
        super(FeedingTube, self).__init__(vocab=vocab, 
                                          token_label='feeding_tube', 
                                          token_patterns=feeding_tube_patterns, 
                                          entity_label='feeding_tube')


class UnitValue(ValueExtractor):
    def __init__(self, vocab, *args, **kwargs):
        
        unit_patterns = [[{"IS_DIGIT": True, "OP": "?"},
                          {"_":{"sci_not": True}, "OP": "?"},
                          {"TEXT": {"REGEX": units_regex}, "OP": "?"}, 
                          {"LOWER": {"IN": ["/", "per"]}}, # 100mg/mL, 10mg/100mL, 10 mg per L...
                          {"IS_DIGIT": True, "OP": "?"}, 
                          {"TEXT": {"REGEX": units_regex}}],
                         [{"IS_DIGIT": True, "OP": "?"}, 
                          {"_":{"sci_not": True}, "OP": "?"},
                          {"TEXT": {"REGEX": units_regex}}], # 20L, 50 mg
                         [{"_": {"decimal": True}}, 
                          {"_":{"sci_not": True}, "OP": "?"}, 
                          {"TEXT": {"REGEX": units_regex}}],
                         [{"_": {"decimal": True}}, 
                          {"_":{"sci_not": True}, "OP": "?"}, 
                          {"TEXT": {"REGEX": units_regex}, "OP": "?"}, 
                          {"LOWER": {"IN": ["/", "per"]}}, # 100mg/mL, 10mg/100mL, 10 mg per L...
                          {"IS_DIGIT": True, "OP": "?"}, 
                          {"TEXT": {"REGEX": units_regex}}],
                         [{"IS_DIGIT": True, "OP": "?"}, 
                          {"_":{"sci_not": True}, "OP": "?"},
                          {"NORM": "unit_num"}, 
                          {"LOWER": {"IN": ["/", "per"]}}, 
                          {"NORM": "unit_denom"}],
                          [{"_": {"decimal": True}}, 
                           {"_":{"sci_not": True}, "OP": "?"},
                           {"NORM": "unit_num"}, 
                           {"LOWER": {"IN": ["/", "per"]}}, 
                           {"NORM": "unit_denom"}],
                           [{"LOWER": "bmi"},
                            {"TEXT": {"IN": ['-', '=', '~', ':', '>', '<']}, "OP": "?"},
                            {"IS_DIGIT": True}],
                           [{"LOWER": "bmi"},
                            {"TEXT": {"IN": ['-', '=', '~', ':', '>', '<']}, "OP": "?"},
                            {"_": {"decimal": True}}]] 
                        
        unit_val_patterns = [[{"IS_DIGIT": True}, {"_":{"sci_not": True}, "OP": "?"}],
                             [{"_": {'decimal': True}}, {"_":{"sci_not": True}, "OP": "?"}], 
                             [{"LOWER": {"IN": ["zero", "o"]}}],
                             [{"_": {'date': True}, 'LENGTH': 3}]]

        unit_norm_patterns = [[{"IS_DIGIT": False,
                                 "_": {"decimal": False, "date": False, "sci_not": False},
                                 "LOWER": {"NOT_IN": ["zero", "o", '-', '=', '~', ':', '>', '<']}}]]

        unit_exclusion_patterns = [[{'LOWER': 'g'}, {'TEXT': '-', 'OP': '?'}, {'LOWER': 'tube'}]]

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
        
        # matches the following forms (with or without punctuation like :, -, =)
            # ecog 4
            # ecog performance status of 4
            # ecog ps 4
            # ecog4
            # ecog=4
            # ecog-4
            # ecog :4

        ecog_exclusion = [{"TEXT": {"FUZZY": {"IN": ["karnofsky", "nodal", "nutrition", "receptor"]}}}]

        ecog_preface = [{"LOWER": "ecog"}, 
                        {"LOWER": {"IN": ["performance", "status", "ps"]}, "OP": "?"}, 
                        {"LOWER": {"IN": ["score", "status", "borderline"]}, "OP": "?"}, 
                        {"LOWER": {"IN": ["is", "now", "=", "still", "of", "~", "currently", "has", "remains", "between", "around", "normally", "was", "improved"]}, "OP": "?"}, \
                        {"LOWER": {"IN": ["been", "at","to", "was"]}, "OP": "?"}, 
                        {"LOWER": {"IN": ["least"]}, "OP": "?"}, 
                        {"IS_PUNCT": True, "OP": "?"}]

        ps_preface = [{"LOWER": {"IN": ["performance", "status", "ps"]}}, 
                      {"LOWER": {"IN": ["score", "status", "borderline"]}, "OP": "?"}, 
                      {"LOWER": {"IN": ["is", "now", "=", "still", "of", "~", "currently", "has", "remains", "normally", "was", "improved"]}, "OP": "?"}, \
                      {"LOWER": {"IN": ["been", "at","to", "was"]}, "OP": "?"}, 
                      {"LOWER": {"IN": ["least"]}, "OP": "?"}, 
                      {"IS_PUNCT": True, "OP": "?"}]

        ecog_patterns = [# ecog_preface + [{"IS_DIGIT": True}],
                         # rare but occasional ecog 2.5
                         ecog_preface + [{"_": {'decimal': True}}], 
                         # special case for when ECOG of 0 is entered as ECOG of O (letter o instead of zero) or written in full
                         ecog_preface + [{"LOWER": {"IN": ["o", "zero", "0", "1", "2", "3", "4"]}}], 
                         # matches additional forms with range e.g. between 1 and 2, 1 to 2
                         ecog_preface + [{"IS_DIGIT": True}, 
                                         {"LOWER": {"IN": ["=", "-", "/", "to", "and", "now"]}}, 
                                         {"IS_DIGIT": True}], 
                         # special case to handle the fact that retokenisation may merge ranges if of the form 1-2 if they meet criteria for date entity
                         ecog_preface + [{"_": {'date': True}, 'LENGTH': 3}],
                         # repeat the above except performance status 2, ps=2 without leading 'ecog'
                         # ps_preface + [{"IS_DIGIT": True}],
                         ps_preface + [{"_": {'decimal': True}}], 
                         ps_preface + [{"LOWER": {"IN": ["o", "zero",  "0", "1", "2", "3", "4"]}}], 
                         ps_preface + [{"IS_DIGIT": True}, \
                                         {"LOWER": {"IN": ["=", "-", "/", "to", "and", "now"]}}, 
                                         {"IS_DIGIT": True}], 
                         ps_preface + [{"_": {'date': True}, 'LENGTH': 3}],
                        # repeat the above except with the exclusion token target
                         ecog_exclusion + ps_preface + [{"IS_DIGIT": True}],
                         ecog_exclusion + ps_preface + [{"_": {'decimal': True}}], 
                         ecog_exclusion + ps_preface + [{"LOWER": {"IN": ["o", "zero"]}}], 
                         ecog_exclusion + ps_preface + [{"IS_DIGIT": True}, \
                                                        {"LOWER": {"IN": ["=", "-", "/", "to", "and", "now"]}}, 
                                                        {"IS_DIGIT": True}], 
                         ecog_exclusion + ps_preface + [{"_": {'date': True}, 'LENGTH': 3}]]
        
        # to match just the numeric portion within an ECOG status entity
        ecog_val_patterns = [[{"TEXT": {"IN": ['0','1','2','3','4']}}], 
                             [{"LOWER": {"IN": ["zero", "o"]}}]]#,
                            # [{"_": {"decimal": True}}]]
                             #[{"_": {'date': True}, 'LENGTH': 3}]]

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


class CaVaLangDefaults(English.Defaults):
    # nixing emoji special cases because they don't matter in this context, and much more likely to be a true equals or a true colon
    #English.Defaults.tokenizer_exceptions = {rule: case for rule, case in English.Defaults.tokenizer_exceptions.items() if rule[0] != ':' and rule[0] != '='}
    tokenizer_exceptions = {rule: case for rule, case in English.Defaults.tokenizer_exceptions.items() if rule[0] != ':' and rule[0] != '='}
    # filtering special cases that are single alpha character followed by a period, as we want to allow for 
    # initials that have been entered as p.o / p.o. / po. etc. when we are re-merging tokens above
    tokenizer_exceptions = {rule: case for rule, case in tokenizer_exceptions.items() if len(rule) != 2 or rule[-1] != '.'}
    # adding in special cases to handle multiple plus signs as short hand for positivity and scale
    for case, rule in special_cases:
        tokenizer_exceptions[case] = rule
    # more enthusiastic tokenisation rules than default english r'\D+\.\D+' r'\D+/\D+'
    infixes = (unit_suffix + list(English.Defaults.infixes)  + ['&', '@', '<', '>', ';', r'\(', r'\)', r'\|', '=', ':', ',', r'\.', r'\/', '~',r'\+\+\+', r'\+\+', r'\+', r'\d+', r'\?'] + spacy.lang.char_classes.LIST_HYPHENS)
    # except that we remove standard unit suffixes so that we can handle more precisely
    suffixes = (unit_suffix + [n for n in list(English.Defaults.suffixes) if 'GB' not in n] + ['@', '~', '<', '>', ';', r'\(', r'\)', r'\|', '=', ':', '/', '-', ',', r'\+\+\+', r'\+\+', r'\+', '--'])
    prefixes = (unit_suffix + [x for x in English.Defaults.prefixes if r'\+' not in x] + ['@', r'\?', '~','<', '>', ';', r'\(', r'\)', r'\|', '-', '=', ':', r'\+\+\+', r'\+\+', r'\+', r'\.', r'\d+', '/'])
    # we are unlikely to care about urls more than we care about sloppy sentence boundaries and missing whitespace around periods
    url_match = None
    create_tokenizer = create_tokenizer



# consider moving these preprocessor steps into a medspacy PreprocessingRule?

def custom_split(input_text, target_char):
    # performs the same as str.split(), whilst making 
    # distinction between spaces / linebreak at the start
    # of the string versus multiple consecutive space / linebreak
    # char within the string
    split_str = []
    line = ''
    for ch in input_text:
        if ch == target_char:
            if line != '':
                split_str.append(line)
            split_str.append('')
            line = ''
        else:  
            line += ch
    if line != '':
        split_str.append(line)
        
    assert len(input_text) == sum([len(l) if len(l) > 0 else 1 for l in split_str])
    return split_str


def whitespace_preprocess(input_text, target_char):
    # this function ensures that exactly one space and one line-break 
    # is retained in an equivalent place in the text for any number of
    # consecutive space or line-break characters.
    # this is done so that basic matchers can be used that do not need
    # to account for inconsistent spacing, which is relatively common.
    
    split_str = custom_split(input_text, target_char)

    a, b = '', ''
    merged_string = []
    if len(split_str) == 1:
        split_str += ['']
    for a, b in zip(split_str[:-1], split_str[1:] + ['']):
        if a != '' or b != '':
            merged_string.append(a)
    if len(merged_string) == 0:
        merged_string.append(a)
    if b != '':
        merged_string.append(b)
    
    return ''.join([m if m != '' else target_char for m in merged_string])


@spacy.registry.languages('cava_lang')
class CaVaLang(English):
    lang = 'cava_lang'
    Defaults = CaVaLangDefaults

    def __call__(self, text, keep_whitespace=False, *args, **kwargs):
        # we don't want to preserve repeated whitespace if using matcher, 
        # but we will preserve linebreaks.  other string pre-processing can be added here

        # this fails when using pre-annotated text because it actually 
        # reduces the text length which then doesn't align with intended spans
        # so make it optional and default to false
        if not keep_whitespace:
            for c in ['\n', ' ']:
                text = whitespace_preprocess(text, c)

        # email pre-processing happens here because we want to tokenise on numbers as infixes
        # so we have too much branching logic to handle emails with numeric elements - bit 
        # hacky but fits here best.
        text = re.sub(emails, lambda x: 'x' * len(x.group()), text)

        return super(CaVaLang, self).__call__(text, *args, **kwargs)
