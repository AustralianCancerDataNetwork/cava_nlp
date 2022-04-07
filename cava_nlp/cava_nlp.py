import spacy
from spacy.lang.en import English
from spacy.symbols import ORTH, NORM
from striprtf.striprtf import rtf_to_text
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokenizer import Tokenizer
from spacy.tokens import Token, Span, Doc
from spacy.lang.en import English, TOKENIZER_EXCEPTIONS

from .tokenizer_exceptions import special_cases, units_regex, unit_suffix, months, ordinal, times, abbv

# retokeniser that allows us to tokenise brutally in the first step (all slashes, all periods, all commas)
# and then reassemble important tokens that shouldn't be broken up such as decimal numbers, units that don't
# fit the basic num/denum form e.g. 10mg/20mL or slashes with no whitespace and alpha characters on both sides
# e.g. O/E or known tumor markers 
@Language.factory("cava_retokenizer")
def create_cava_retokenizer(nlp, name):
    return CaVaRetokenizer(nlp.vocab)

class CaVaRetokenizer:
    def __init__(self, vocab):

        unit_patterns = [[{"IS_DIGIT": True, "OP": "?"}, {"TEXT": {"REGEX": units_regex}}, {"LOWER": {"IN": ["/", "per"]}}, {"IS_DIGIT": True, "OP": "?"}, {"TEXT": {"REGEX": units_regex}}],
                         [{"IS_DIGIT": True, "OP": "?"}, {"TEXT": {"REGEX": units_regex}}]]
                
        decimal_patterns = [[{"IS_DIGIT": True}, {"ORTH": {"IN": ['.', ',']}}, {"IS_DIGIT": True}]]
        
        unit_val_patterns = [[{"IS_DIGIT": True}]]

        date_patterns = [[{"IS_DIGIT": True}, {"ORTH": {"IN": ["/", "-"]}}, {"IS_DIGIT": True},  {"ORTH": {"IN": ["/", "-"]}}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20
                         [{"IS_DIGIT": True},  {"ORTH": {"IN": ["/", "-"]}}, {"IS_DIGIT": True}], # 1/2020, 1-2020
                         [{"IS_DIGIT": True}, {"ORTH": {"IN": ["/", "-"]}, "OP": "?"}, {"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-"]}, "OP": "?"}, {"IS_DIGIT": True, "OP": "?"}], # 1-Jan-20, 1/jan/20
                         [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?"}, {"IS_DIGIT": True}], # Jan/2020, Jan 2020, Jan '20
                         [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?"}, {"TEXT": {"REGEX": ordinal}}]]
        
        time_patterns = [[{"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}}, {"IS_DIGIT": True}, {"LOWER": {"IN": times}}]]

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

        self.date_matcher = Matcher(vocab)
        self.time_matcher = Matcher(vocab)
        self.unit_matcher = Matcher(vocab)
        self.decimal_matcher = Matcher(vocab)
        self.unit_val_matcher = Matcher(vocab)
        self.other = Matcher(vocab)
        
        self.date_matcher.add("date", date_patterns)
        self.unit_matcher.add("unit", unit_patterns)#, on_match=get_ecog_value)
        self.decimal_matcher.add("decimal", decimal_patterns)
        self.unit_val_matcher.add("unit_val", unit_val_patterns)
        self.time_matcher.add("time", time_patterns)
        self.other.add("other", other_remerge)

    def set_extension(self, token, name):
        token._.__setattr__(name, True)
        
    def merge_spans(self, matches, doc, name=""):
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
                if token.is_digit:
                    self.set_extension(token, 'unit_value')
                elif token.text.lower() not in ['/', 'per']:
                    self.set_extension(token, 'unit')
                    
    def __call__(self, doc):
        self.merge_spans(self.decimal_matcher(doc), doc, 'decimal')
        self.merge_spans(self.date_matcher(doc), doc, 'date')
        self.merge_spans(self.time_matcher(doc), doc, 'time')
        self.set_units(self.unit_matcher(doc), doc)
        self.merge_spans(self.other(doc), doc)
        return doc

# rule-based matcher for extracting ecog status
@Language.factory("ecog_status")
def create_ecog_status(nlp, name):
    return ECOGStatus(nlp.vocab)

@Language.component("whitespace_merger")
def whitspace_merger(doc):
    # we don't want to preserve repeated whitespace if using matcher, 
    # but we will preserve linebreaks
    return Doc(doc.vocab, [t.text for t in doc if not t.is_space and not ''.join(set(t.text)) == ' '])

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
    infixes = (unit_suffix + list(English.Defaults.infixes)  + ['<', '>', ';', '\(', '\)', '\|', '=', ':', ',', '\.', '/', '~','\+\+\+', '\+\+', '\+', '\d+'] + spacy.lang.char_classes.LIST_HYPHENS)
    # except that we remove standard unit suffixes so that we can handle more precisely
    suffixes = (unit_suffix + [n for n in list(English.Defaults.suffixes) if 'GB' not in n] + ['~', '<', '>', ';', '\(', '\)', '\|', '=', ':', '/', '-', ',', '\+\+\+', '\+\+', '\+', '--'])
    prefixes = (unit_suffix + [x for x in English.Defaults.prefixes if '\+' not in x] + ['\?', '~','<', '>', ';', '\(', '\)', '\|', '-', '=', ':', '\+\+\+', '\+\+', '\+', '\.', '\d+', '/'])
    # we are unlikely to care about urls more than we care about sloppy sentence boundaries and missing whitespace around periods
    url_match = None

@spacy.registry.languages('cava_lang')
class CaVaLang(English):
    lang = 'cava_lang'
    Defaults = CaVaLangDefaults
