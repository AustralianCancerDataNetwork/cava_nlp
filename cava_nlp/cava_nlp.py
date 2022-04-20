import spacy, re
from spacy.lang.en import English
from spacy.symbols import ORTH, NORM
from striprtf.striprtf import rtf_to_text
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokenizer import Tokenizer
from spacy.tokens import Token, Span, Doc
from spacy.lang.en import English, TOKENIZER_EXCEPTIONS

from .tokenizer_exceptions import special_cases, units_regex, unit_suffix, months, ordinal, times, abbv, no_whitespace, emails, day_regex, year_regex, numeric_month_regex

# retokeniser that allows us to tokenise brutally in the first step (e.g. all slashes, all periods, all commas)
# and then reassemble important tokens that shouldn't be broken up such as decimal numbers, units that don't
# fit the basic num/denum form e.g. 10mg/20mL or slashes with no whitespace and alpha characters on both sides
# e.g. O/E or known tumor markers 
@Language.factory("cava_retokenizer")
def create_cava_retokenizer(nlp, name):
    return CaVaRetokenizer(nlp.vocab)

@spacy.registry.tokenizers("cava.Tokenizer.v1")
def create_tokenizer():

    def tokenizer_factory(nlp):
        prefixes = nlp.Defaults.prefixes
        suffixes = nlp.Defaults.suffixes
        infixes = nlp.Defaults.infixes

        prefix_search = spacy.util.compile_prefix_regex(prefixes).search if prefixes else None
        suffix_search = spacy.util.compile_suffix_regex(suffixes).search if suffixes else None
        infix_finditer = spacy.util.compile_infix_regex(infixes).finditer if infixes else None

        return CaVaRetokenizer(nlp.vocab,
                               rules = nlp.Defaults.tokenizer_exceptions,
                               prefix_search = prefix_search,
                               suffix_search = suffix_search,
                               infix_finditer = infix_finditer, 
                               token_match = nlp.Defaults.token_match,
                               url_match = nlp.Defaults.url_match)

    return tokenizer_factory

class CavaMatcher(Matcher):

    def __init__(self, *args, **kwargs):
        super(CavaMatcher, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return super(CavaMatcher, self).__call__(*args, **kwargs)


class CaVaRetokenizer(Tokenizer):

    def __init__(self, vocab, rules, prefix_search, suffix_search, 
                       infix_finditer, token_match, url_match):
        
        super(CaVaRetokenizer, self).__init__(vocab, rules, prefix_search, suffix_search, 
                                              infix_finditer, token_match, url_match)


        unit_patterns = [[{"IS_DIGIT": True, "OP": "?"}, {"TEXT": {"REGEX": units_regex}}, 
                          {"LOWER": {"IN": ["/", "per"]}}, # 100mg/mL, 10mg/100mL, 10 mg per L...
                          {"IS_DIGIT": True, "OP": "?"}, {"TEXT": {"REGEX": units_regex}}],
                         [{"IS_DIGIT": True, "OP": "?"}, {"TEXT": {"REGEX": units_regex}}], # 20L, 50 mg
                         [{"_": {"decimal": True}},
                          {"TEXT": {"REGEX": units_regex}}]] # 3.5cm
                
        decimal_patterns = [[{"IS_DIGIT": True}, {"ORTH": {"IN": ['.', ',']}}, {"IS_DIGIT": True}]]

        date_patterns = [[{"IS_DIGIT": True}, {"ORTH": {"IN": ["/", "-"]}}, {"IS_DIGIT": True},  {"ORTH": {"IN": ["/", "-"]}}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20 - keep as digit based because 3 part unlikely to be false pos 
                         [{"TEXT": {"REGEX": numeric_month_regex}},  {"ORTH": {"IN": ["/"]}}, {"TEXT": {"REGEX": year_regex}}], # 1/2020, 1-2020 - changed from is digit to avoid false pos with BP
                         [{"TEXT": {"REGEX": day_regex}},  {"ORTH": {"IN": ["/"]}}, {"TEXT": {"REGEX": numeric_month_regex}}], # 31/12
                         [{"IS_DIGIT": True}, {"ORTH": {"IN": ["/", "-"]}, "OP": "?"}, {"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-"]}, "OP": "?"}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # 1-Jan-20, 1/jan/20
                         [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?"}, {"TEXT": {"REGEX": year_regex}}], # Jan/2020, Jan 2020, Jan '20
                         [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?"}, {"TEXT": {"REGEX": ordinal}}]] # September 4th
        dp = [] # dates must either start sentence or have preceding space, to avoid false pos with spinal notation e.g. C3/4
        for d in date_patterns:
            dp.append([{"IS_SENT_START": True}] + d)
            dp.append([{"SPACY": True}] + d)

        time_patterns = [[{"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}}, {"IS_DIGIT": True}, {"LOWER": {"IN": times}}]]

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
        
        Token.set_extension("unit", default=False, force=True)
        Token.set_extension("unit_value", default=False, force=True)
        Token.set_extension("decimal", default=False, force=True)
        Token.set_extension("date", default=False, force=True)
        Token.set_extension("time", default=False, force=True)

        self.date_matcher = CavaMatcher(vocab)
        self.time_matcher = CavaMatcher(vocab)
        self.unit_matcher = CavaMatcher(vocab)
        self.decimal_matcher = CavaMatcher(vocab)
        self.query_matcher = CavaMatcher(vocab)
        self.other = CavaMatcher(vocab)
        
        self.date_matcher.add("date", dp)
        self.unit_matcher.add("unit", unit_patterns)
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
      
    def set_units(self, matches, doc, name=""):
        spans = []  # Collect the matched spans here
        for match_id, start, end in matches:
            spans.append(doc[start:end])
        for span in spacy.util.filter_spans(spans):
            for token in span:
                if token.is_digit or token._.decimal:
                    self.set_extension(token, 'unit_value')
                elif token.text.lower() not in ['/', 'per']:
                    self.set_extension(token, 'unit')

    def mark_queries(self, matches, doc):
        # this gives a question mark at the start of a word with no whitespace in between
        # the norm of 'query', as per '??' and '???', but question marks at the end of a 
        # sentence are left as-is
        for match_id, start, end in matches:
            if doc[start].whitespace_ == '':
                doc[start].norm_ = 'query'
                    
    def __call__(self, doc):
        doc = super(CaVaRetokenizer, self).__call__(doc)
        self.merge_spans(self.decimal_matcher(doc), doc, 'decimal')
        self.merge_spans(self.date_matcher(doc), doc, 'date', True)
        self.merge_spans(self.time_matcher(doc), doc, 'time')
        self.set_units(self.unit_matcher(doc), doc)
        self.merge_spans(self.other(doc), doc)
        self.mark_queries(self.query_matcher(doc), doc)
        return doc

# rule-based matcher for extracting ecog status
@Language.factory("ecog_status")
def create_ecog_status(nlp, name):
    return ECOGStatus(nlp.vocab)

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
    
class ECOGStatus:
    def __init__(self, vocab):
        
                        # matches the following forms (with or without punctuation like :, -, =)
                            # ecog 4
                            # ecog performance status of 4
                            # ecog ps 4
                            # ecog4
                            # ecog=4
                            # ecog-4
                            # ecog :4
        ecog_patterns = [[{"LOWER": "ecog"}, 
                          {"LOWER": {"IN": ["performance", "status", "ps"]}, "OP": "?"}, 
                          {"LOWER": {"IN": ["score", "status", "borderline"]}, "OP": "?"}, 
                          {"LOWER": {"IN": ["is", "now", "=", "still", "of", "~", "currently", "has", "remains", "normally"]}, "OP": "?"}, \
                          {"LOWER": {"IN": ["been", "at"]}, "OP": "?"}, \
                          {"IS_PUNCT": True, "OP": "?"}, {"IS_DIGIT": True}], \
                         # special case for when ECOG of 0 is entered as ECOG of O (letter o instead of zero) or written in full
                         [{"LOWER": "ecog"}, 
                          {"LOWER": {"IN": ["performance", "status", "ps"]}, "OP": "?"}, 
                          {"LOWER": {"IN": ["score", "status", "borderline"]}, "OP": "?"}, 
                          {"LOWER": {"IN": ["is", "now", "=", "still", "of", "~", "currently", "has", "remains", "normally"]}, "OP": "?"}, \
                          {"LOWER": {"IN": ["been", "at"]}, "OP": "?"}, \
                          {"IS_PUNCT": True, "OP": "?"}, {"LOWER": {"IN": ["o", "zero"]}}], \
                         # matches additional forms with range 1-2, 1 to 2
                         [{"LOWER": "ecog"}, 
                          {"LOWER": {"IN": ["performance", "status", "ps"]}, "OP": "?"}, 
                          {"LOWER": {"IN": ["score", "status", "borderline"]}, "OP": "?"}, 
                          {"LOWER": {"IN": ["is", "now", "=", "still", "of", "~", "currently", "has", "remains", "between", "normally"]}, "OP": "?"}, \
                          {"LOWER": {"IN": ["been", "at"]}, "OP": "?"}, \
                          {"IS_PUNCT": True, "OP": "?"}, 
                          {"IS_DIGIT": True}, \
                          {"IS_PUNCT": True, "OP": "?"}, 
                          {"LOWER": {"IN": ["to", "and"]}, "OP": "?"}, 
                          {"IS_DIGIT": True}]]
        
        # to match just the numeric portion within an ECOG status entity
        ecog_val_patterns = [[{"IS_DIGIT": True}], [{"LOWER": {"IN": ["zero", "o"]}}]]

        # Register a new token extension to flag ecog status custom attribute
        Token.set_extension("ecog_status", default=False)
        Token.set_extension("ecog_status_value", default=-1)
        self.ecog_matcher = Matcher(vocab)
        self.ecog_matcher.add("ecog", ecog_patterns, on_match=add_ecog_ent)
        self.ecog_value = Matcher(vocab)
        self.ecog_value.add("ecog", ecog_val_patterns)#, on_match=get_ecog_value)
        
    def __call__(self, doc):
        # This method is invoked when the component is called on a Doc
        matches = self.ecog_matcher(doc) 
        spans = []  # Collect the matched spans here
        for match_id, start, end in matches:
            spans.append(doc[start:end])
        with doc.retokenize() as retokenizer:
            for span in spacy.util.filter_spans(spans):
                value_matches = self.ecog_value(span)
                values = [-1]
                for value_id, v_start, v_end in value_matches:
                    try:
                        values.append(int(span[v_start:v_end].text))
                    except:
                        values.append(0) # the only non-numeric entries currently tolerated are 'zero' or 'o'
                retokenizer.merge(span)
                for token in span:
                    token._.ecog_status = True  
                    token._.ecog_status_value = max(values)
        return doc


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
    infixes = (unit_suffix + list(English.Defaults.infixes)  + ['&', '@', '<', '>', ';', '\(', '\)', '\|', '=', ':', ',', '\.', '/', '~','\+\+\+', '\+\+', '\+', '\d+', '\?'] + spacy.lang.char_classes.LIST_HYPHENS)
    # except that we remove standard unit suffixes so that we can handle more precisely
    suffixes = (unit_suffix + [n for n in list(English.Defaults.suffixes) if 'GB' not in n] + ['@', '~', '<', '>', ';', '\(', '\)', '\|', '=', ':', '/', '-', ',', '\+\+\+', '\+\+', '\+', '--'])
    prefixes = (unit_suffix + [x for x in English.Defaults.prefixes if '\+' not in x] + ['@', '\?', '~','<', '>', ';', '\(', '\)', '\|', '-', '=', ':', '\+\+\+', '\+\+', '\+', '\.', '\d+', '/'])
    # we are unlikely to care about urls more than we care about sloppy sentence boundaries and missing whitespace around periods
    url_match = None
    create_tokenizer = create_tokenizer

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
    skips, merged_string = [], []
    if len(split_str) == 1:
        split_str += ['']
    for a, b in zip(split_str[:-1], split_str[1:] + ['']):
        if a == '' and b == '':
            skips.append(0)
        else:
            skips.append(max(1, len(a)))
            merged_string.append(a)
    if len(merged_string) == 0:
        merged_string.append(a)
    skips.append(len(b))
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
