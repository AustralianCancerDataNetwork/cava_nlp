# import spacy, re, medspacy
# from spacy.lang.en import English
# from spacy.symbols import ORTH, NORM
# from striprtf.striprtf import rtf_to_text
# from spacy.language import Language
# from spacy.matcher import Matcher
# from spacy.tokenizer import Tokenizer
# from spacy.tokens import Token, Span, Doc
# from spacy.lang.en import English, TOKENIZER_EXCEPTIONS

# from .tokenization.tokenizer_exceptions import special_cases, units_regex, unit_suffix, months, ordinal, \
#                                   times, abbv, no_whitespace, emails, day_regex, year_regex, \
#                                   numeric_month_regex, scientific_notation, weight_units
# from .sectionizer.sectionizer_config import get_sectionizer_attrs, get_sectionizer_patterns, get_dated_sectionizer_patterns
# from .context.context_config import get_context_attrs, get_context_patterns

# # retokeniser that allows us to tokenise brutally in the first step (e.g. all slashes, all periods, all commas)
# # and then reassemble important tokens that shouldn't be broken up such as decimal numbers, units that don't
# # fit the basic num/denum form e.g. 10mg/20mL or slashes with no whitespace and alpha characters on both sides
# # e.g. O/E or known tumor markers 

# @Language.factory("cava_retokenizer")
# def create_cava_retokenizer(nlp, name):
#     return CaVaRetokenizer(nlp)

# @spacy.registry.tokenizers("cava.Tokenizer.v1")
# def create_tokenizer():

#     def tokenizer_factory(nlp):
#         return CaVaRetokenizer(nlp)#.vocab,
#                             #    rules = nlp.Defaults.tokenizer_exceptions,
#                             #    prefix_search = prefix_search,
#                             #    suffix_search = suffix_search,
#                             #    infix_finditer = infix_finditer, 
#                             #    token_match = nlp.Defaults.token_match,
#                             #    url_match = nlp.Defaults.url_match)

#     return tokenizer_factory

# class CaVaMatcher(Matcher):

#     def __init__(self, *args, **kwargs):
#         super(CaVaMatcher, self).__init__(*args, **kwargs)

#     def __call__(self, *args, **kwargs):
#         return super(CaVaMatcher, self).__call__(*args, **kwargs)


# # class CaVaRetokenizer(Tokenizer):

# #     def __init__(self, nlp): # vocab, rules, prefix_search, suffix_search, 
# #                              # infix_finditer, token_match, url_match):
# #         prefixes = nlp.Defaults.prefixes
# #         suffixes = nlp.Defaults.suffixes
# #         infixes = nlp.Defaults.infixes

# #         prefix_search = spacy.util.compile_prefix_regex(prefixes).search if prefixes else None
# #         suffix_search = spacy.util.compile_suffix_regex(suffixes).search if suffixes else None
# #         infix_finditer = spacy.util.compile_infix_regex(infixes).finditer if infixes else None
        
# #         super(CaVaRetokenizer, self).__init__(nlp.vocab, nlp.Defaults.tokenizer_exceptions, 
# #                                               prefix_search, suffix_search, 
# #                                               infix_finditer, nlp.Defaults.token_match, 
# #                                               nlp.Defaults.url_match)

# #         sci_notation_patterns = [[{"LOWER":"x", "OP": "?"},
# #                                   {"TEXT": "10"}, 
# #                                   {"LOWER":"x", "OP": "?"},
# #                                   {"TEXT": {"IN":["^", "**"]}},
# #                                   {"IS_DIGIT": True}],
# #                                   [{"IS_DIGIT": True},
# #                                    {"LOWER": "e"},
# #                                    {"TEXT": "+", "OP": "?"},
# #                                    {"IS_DIGIT": True}]
# #                                 ]

# #         decimal_patterns = [[{"IS_DIGIT": True, "LIKE_NUM": True}, 
# #                              {"ORTH": {"IN": ['.', ',']}, 'SPACY': False}, 
# #                              {"IS_DIGIT": True, "LIKE_NUM": True}]]

# #         date_patterns = [[{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "-", "SPACY": False}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20 - keep as digit based because 3 part unlikely to be false pos 
# #                          [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "-", "SPACY": False}, {"IS_DIGIT": True}, {"IS_DIGIT": True}, {"ORTH": ":", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": ":", "SPACY": False}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20 with times HH:MM:SS
# #                          [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "/", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "/", "SPACY": False}, {"IS_DIGIT": True}], # no longer expressed as 'in', as we really want the separators to be the same
# #                          [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": ".", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": ".", "SPACY": False}, {"IS_DIGIT": True}], 
# #                          [{"TEXT": {"REGEX": numeric_month_regex}, 'SPACY': False},  {"ORTH": {"IN": ["/", "-"]}, 'SPACY': False}, {"TEXT": {"REGEX": year_regex}}], # 1/2020, 1-2020 - changed from is digit to avoid false pos with BP
# #                          [{"TEXT": {"REGEX": day_regex}, 'SPACY': False},  {"ORTH": {"IN": ["/", "-"]}, 'SPACY': False}, {"TEXT": {"REGEX": numeric_month_regex}}], # 31/12
# #                          [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "/", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": "/", "SPACY": False}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # 1-Jan-20, 1/jan/20
# #                          [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": "-", "SPACY": False}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # no longer expressed as 'in', as we really want the separators to be the same
# #                          [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": ".", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": ".", "SPACY": False}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], 
# #                          [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": numeric_month_regex}}, {"TEXT": {"REGEX": ordinal}}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # September 4th
# #                          [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": year_regex}}], # Jan/2020, Jan 2020, Jan '20
# #                          [{"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": numeric_month_regex}}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}]] # September 4th

# #         dp = [[],[]] # dates must either start sentence or have preceding space, to avoid false pos with spinal notation e.g. C3/4
# #         for d in date_patterns:
# #             dp[0].append([{"SPACY": True}] + d)
# #             dp[0].append([{"TEXT": {"IN": ["\n", "\n\n", '-']}}] + d)
# #             sent_start = [attr.copy() for attr in d]
# #             sent_start[0]["IS_SENT_START"] = True
# #             dp[1].append(sent_start)

# #         time_patterns = [[{"ORTH": "@", "OP": "?"}, 
# #                           {"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}}, 
# #                           {"IS_DIGIT": True}, {"LOWER": {"IN": times}}],
# #                          [{"ORTH": "@", "OP": "?"}, 
# #                           {"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}}, 
# #                           {"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}}, 
# #                           {"IS_DIGIT": True}, {"LOWER": {"IN": times}}],
# #                           [{"ORTH": "@", "OP": "?"},  
# #                           {"IS_DIGIT": True}, {"LOWER": {"IN": times}}],
# #                           [{"ORTH": "@", "OP": "?"}, {"IS_DIGIT": True}, {"ORTH": {"IN": [":", "-", "."]}, "SPACY": False}, 
# #                            {"IS_DIGIT": True, "SPACY": False}, {"ORTH": {"IN": [":", "-", "."]}, "SPACY": False}, 
# #                            {"IS_DIGIT": True, "SPACY": False}]]

# #         # making sure we can mark a question mark at the beginning of a word as a query despite it being tokenised
# #         # e.g. ?query timing
# #         query_patterns = [[{"TEXT": {"IN": ["?"]}}, {"IS_ALPHA": True}]]

# #         # these are non-specific merge steps that will re-join alphanumeric tokens split by a slash, 
# #         # or tokens that appear to be actual acronyms (single chars split by period) p.o, p.o., a.b.v etc.
# #         other_remerge = [[{"TEXT": {"REGEX": abbv}}, {"ORTH": "/"}, {"TEXT": {"REGEX": abbv}}],
# #                          [{"TEXT": {"REGEX": abbv}}, {"ORTH": '.', "OP": "?"}, {"IS_DIGIT": True}],
# #                          [{"TEXT": {"REGEX": abbv}}, {"IS_DIGIT": True}, {"TEXT": {"REGEX": abbv}}, {"IS_DIGIT": True}],
# #                          [{"TEXT": {"REGEX": abbv}}, {"ORTH": '.'}, {"TEXT": {"REGEX": abbv}}, {"ORTH": '.', "OP": "?"}],
# #                          [{"TEXT": {"REGEX": abbv}}, {"ORTH": '.'}, {"TEXT": {"REGEX": abbv}}, {"ORTH": '.'}, {"TEXT": {"REGEX": abbv}}, {"ORTH": '.', "OP": "?"}]]
        
# #         Token.set_extension("sci_not", default=False, force=True)
# #         Token.set_extension("decimal", default=False, force=True)
# #         Token.set_extension("date", default=False, force=True)
# #         Token.set_extension("time", default=False, force=True)

# #         self.date_matcher_skip = CaVaMatcher(nlp.vocab)
# #         self.date_matcher = CaVaMatcher(nlp.vocab)
# #         self.time_matcher = CaVaMatcher(nlp.vocab)
# #         self.decimal_matcher = CaVaMatcher(nlp.vocab)
# #         self.query_matcher = CaVaMatcher(nlp.vocab)
# #         self.sci_not_matcher = CaVaMatcher(nlp.vocab)
# #         self.other = CaVaMatcher(nlp.vocab)
        
# #         self.date_matcher_skip.add("date", dp[0])
# #         self.date_matcher.add("date", dp[1])
# #         self.sci_not_matcher.add("sci_not", sci_notation_patterns)
# #         self.decimal_matcher.add("decimal", decimal_patterns)
# #         self.time_matcher.add("time", time_patterns)
# #         self.query_matcher.add("query", query_patterns)
# #         self.other.add("other", other_remerge)

# #     def set_extension(self, token, name):
# #         token._.__setattr__(name, True)
        
# #     def merge_spans(self, matches, doc, name="", skip_first=False):
# #         spans = []  # Collect the matched spans here
# #         for match_id, start, end in matches:
# #             spans.append(doc[start:end])
# #         # if no named extension, we allow matches only if first token in span does not have 
# #         # trailing whitespace. this is because the unnamed merges are less specific and 
# #         # more inclined to create false pos matches
# #         with doc.retokenize() as retokenizer:
# #             for span in spacy.util.filter_spans(spans):
# #                 if name == "" and len([s for s in span[:-1] if s.whitespace_]) > 0:
# #                     continue
# #                 # skipping first token in match for dates only at this point, because we look backwards to check for space
# #                 if skip_first:
# #                     span = span[1:]
# #                 retokenizer.merge(span)
# #                 if name != "":
# #                     for token in span:
# #                         self.set_extension(token, name) 
      
# #     def mark_queries(self, matches, doc):
# #         # this gives a question mark at the start of a word with no whitespace in between
# #         # the norm of 'query', as per '??' and '???', but question marks at the end of a 
# #         # sentence are left as-is
# #         for match_id, start, end in matches:
# #             if doc[start].whitespace_ == '':
# #                 doc[start].norm_ = 'query'
                    
# #     def __call__(self, doc):
# #         doc = super(CaVaRetokenizer, self).__call__(doc)
# #         self.merge_spans(self.date_matcher_skip(doc), doc, 'date', True)
# #         self.merge_spans(self.date_matcher(doc), doc, 'date')
# #         self.merge_spans(self.time_matcher(doc), doc, 'time')
# #         self.merge_spans(self.decimal_matcher(doc), doc, 'decimal')
# #         self.merge_spans(self.sci_not_matcher(doc), doc, 'sci_not')
# #         self.mark_queries(self.query_matcher(doc), doc)
# #         return doc

# # # trained NER for extracting oral drugs
# # @Language.factory("oral_meds")
# # def ..

# class CaVaLangDefaults(English.Defaults):
#     # nixing emoji special cases because they don't matter in this context, and much more likely to be a true equals or a true colon
#     #English.Defaults.tokenizer_exceptions = {rule: case for rule, case in English.Defaults.tokenizer_exceptions.items() if rule[0] != ':' and rule[0] != '='}
#     tokenizer_exceptions = {rule: case for rule, case in English.Defaults.tokenizer_exceptions.items() if rule[0] != ':' and rule[0] != '='}
#     # filtering special cases that are single alpha character followed by a period, as we want to allow for 
#     # initials that have been entered as p.o / p.o. / po. etc. when we are re-merging tokens above
#     tokenizer_exceptions = {rule: case for rule, case in tokenizer_exceptions.items() if len(rule) != 2 or rule[-1] != '.'}
#     # adding in special cases to handle multiple plus signs as short hand for positivity and scale
#     for case, rule in special_cases:
#         tokenizer_exceptions[case] = rule
#     # more enthusiastic tokenisation rules than default english r'\D+\.\D+' r'\D+/\D+'
#     infixes = (unit_suffix + list(English.Defaults.infixes)  + ['&', '@', '<', '>', ';', r'\(', r'\)', r'\|', '=', ':', ',', r'\.', r'\/', '~',r'\+\+\+', r'\+\+', r'\+', r'\d+', r'\?'] + spacy.lang.char_classes.LIST_HYPHENS)
#     # except that we remove standard unit suffixes so that we can handle more precisely
#     suffixes = (unit_suffix + [n for n in list(English.Defaults.suffixes) if 'GB' not in n] + ['@', '~', '<', '>', ';', r'\(', r'\)', r'\|', '=', ':', '/', '-', ',', r'\+\+\+', r'\+\+', r'\+', '--'])
#     # note PGSGA special prefixes for handling instances where spaces are missed in the score e.g. PGSGAB12
#     prefixes = (unit_suffix + [x for x in English.Defaults.prefixes if r'\+' not in x] + ['@', r'\?', '~','<', '>', ';', r'\(', r'\)', r'\|', '-', '=', ':', r'\+\+\+', r'\+\+', r'\+', r'\.', r'\d+', '/', 'SGA', 'PGSGA'])
#     # we are unlikely to care about urls more than we care about sloppy sentence boundaries and missing whitespace around periods
#     url_match = None
#     create_tokenizer = create_tokenizer

# # consider moving these preprocessor steps into a medspacy PreprocessingRule?

# def custom_split(input_text, target_char):
#     # performs the same as str.split(), whilst making 
#     # distinction between spaces / linebreak at the start
#     # of the string versus multiple consecutive space / linebreak
#     # char within the string
#     split_str = []
#     line = ''
#     for ch in input_text:
#         if ch == target_char:
#             if line != '':
#                 split_str.append(line)
#             split_str.append('')
#             line = ''
#         else:  
#             line += ch
#     if line != '':
#         split_str.append(line)
        
#     assert len(input_text) == sum([len(l) if len(l) > 0 else 1 for l in split_str])
#     return split_str


# def whitespace_preprocess(input_text, target_char):
#     # this function ensures that exactly one space and one line-break 
#     # is retained in an equivalent place in the text for any number of
#     # consecutive space or line-break characters.
#     # this is done so that basic matchers can be used that do not need
#     # to account for inconsistent spacing, which is relatively common.
    
#     split_str = custom_split(input_text, target_char)

#     a, b = '', ''
#     merged_string = []
#     if len(split_str) == 1:
#         split_str += ['']
#     for a, b in zip(split_str[:-1], split_str[1:] + ['']):
#         if a != '' or b != '':
#             merged_string.append(a)
#     if len(merged_string) == 0:
#         merged_string.append(a)
#     if b != '':
#         merged_string.append(b)
    
#     return ''.join([m if m != '' else target_char for m in merged_string])


# @spacy.registry.languages('cava_lang')
# class CaVaLang(English):
#     lang = 'cava_lang'
#     Defaults = CaVaLangDefaults

#     def __init__(self, with_section_context=False, with_dated_section_context=False, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # we default to medspacy sentencizer as it's much better than the spacy one for clinical text - pysbd handles
#         # new lines more intelligently than pyrush
#         self.add_pipe('medspacy_pysbd')
#         if with_section_context or with_dated_section_context:
#             # note that with_dated_section_context=True overrides with_section_context when both are provided
#             sectionizer_config = {'rules': None, 'span_attrs': get_sectionizer_attrs()}
#             sectionizer_type = 'dated_sectionizer' if with_dated_section_context else 'medspacy_sectionizer'
#             sectionizer_patterns = get_dated_sectionizer_patterns if with_dated_section_context else get_sectionizer_patterns
#             sectionizer = self.add_pipe(sectionizer_type, config=sectionizer_config)
#             sectionizer.add(sectionizer_patterns())
#             # #medspacy.load(self, medspacy_disable=['medspacy_tokenizer', 'medspacy_context', 'medspacy_target_matcher'])
#             # sectionizer = self.add_pipe('medspacy_sectionizer', config={'rules': None, 'span_attrs': get_sectionizer_attrs()})
#             # sectionizer.add(get_sectionizer_patterns())
#             context = self.add_pipe('medspacy_context', config={'span_attrs': get_context_attrs(), 
#                                                                 'rules': str(get_context_patterns())})#, 'terminating_types': {'CURRENT': ['NEW_SECTION'], 'HISTORICAL': ['NEW_SECTION']}})
        

#     def __call__(self, text, whitespace_strip=[' '],  *args, **kwargs):
#         # we don't want to preserve repeated whitespace if using matcher, 
#         # but we will preserve linebreaks.  other string pre-processing can be added here

#         # this fails when using pre-annotated text because it actually 
#         # reduces the text length which then doesn't align with intended spans
#         # so make it optional and default to false
#         for c in whitespace_strip: # intended to be set to either just merging consecutive spaces and/or consecutive linebreaks, or just empty list if we will preserve all - ['\n', ' ']:
#             text = whitespace_preprocess(text, c)

#         # email pre-processing happens here because we want to tokenise on numbers as infixes
#         # so we have too much branching logic to handle emails with numeric elements - bit 
#         # hacky but fits here best.
#         text = re.sub(emails, lambda x: 'x' * len(x.group()), text)

#         return super(CaVaLang, self).__call__(text, *args, **kwargs)
