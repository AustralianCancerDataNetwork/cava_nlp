from cava_nlp.namespaces.regex import weight_units, units_regex

weight_patterns = [[{"_":{"unit": True}, "NORM": {"IN": weight_units}}]]

# pgsga_preface = [{"LOWER": {"IN": ['pg', 'pgsga', 'psgsga', 'sga', 'psga', 'psgag']}},
#                  {"TEXT": {"IN": ["-", '_', ":"]}, "OP": "?"},
#                  {"LOWER": "sga", "OP": "?"},
#                  {"LOWER": {"IN": ["short", "sf"]}, "OP": "?"},
#                  {"LOWER": {"IN": ["score", "rating", "form", "shortform", "from"]}, "OP": "?"},
#                  {"LOWER": "and", "OP": "?"},
#                  {"TEXT": {"IN": ["(", "/"]}, "OP": "?"},
#                  {"LOWER": {"IN": ["score", "rating"]}, "OP": "?"},
#                  {"LOWER": {"IN": ["-", '_', ":", "=", "of"]}, "OP": "?"},
#                  ]


pgsga_val_patterns = [#[{"TEXT": {"REGEX": r"\d[abc]"}}],
                      [{"TEXT": {"IN": ["("]}, "OP": "?"}, 
                       {"IS_DIGIT": True},
                       {"TEXT": {"IN": ["/", ","]},  "OP": "?"},
                       {"LOWER": "rating", "OP": "?"},
                       {"TEXT": {"IN": ["("]}, "OP": "?"}, 
                       {"LOWER": {"IN": ['a', 'b', 'c']}},
                       {"TEXT": {"IN": [")"]}, "OP": "?"}],
                      [{"TEXT": {"IN": ["("]}, "OP": "?"}, 
                       {"LOWER": {"IN": ['a', 'b', 'c']}},
                       {"TEXT": {"IN":["/", '-']},  "OP": "?"},
                       {"TEXT": {"IN": ["("]}, "OP": "?"},
                       {"IS_DIGIT": True},
                       {"TEXT": {"IN": [")"]}, "OP": "?"}],
                      [{"TEXT": {"IN": ["("]}, "OP": "?"}, 
                       {"LOWER": {"IN": ['a', 'b', 'c']}},                       
                       {"TEXT": {"IN": [")"]}, "OP": "?"}],
                      [{"TEXT": {"IN": ["("]}, "OP": "?"}, 
                       {"IS_DIGIT": True},
                       {"TEXT": {"IN": [")"]}, "OP": "?"}]]
        
pgsga_preface = [
 [{"LOWER": 'pg'},{"TEXT": {"IN": ["-", '_', ":"]}, "OP": "?"},{"LOWER": "sga"}],
 [{"LOWER": {"IN": [ 'pgsga', 'psgsga', 'psga', 'psgag']}},{"TEXT": {"IN": ["-", '_', ":"]}, "OP": "?"}]
]

score_preface = [{"LOWER": {"IN": ["short", "sf"]}, "OP": "?"},
                 {"LOWER": {"IN": ["score", "rating", "form", "shortform", "from"]}, "OP": "?"},
                 {"LOWER": "and", "OP": "?"},
                 {"TEXT": {"IN": ["(", "/"]}, "OP": "?"},
                 {"LOWER": {"IN": ["score", "rating"]}, "OP": "?"},
                 {"LOWER": {"IN": ["-", '_', ":", "=", "of"]}, "OP": "?"}]

pgsga_patterns = [x for y in [[pref + pp for pref in [p + score_preface for p in pgsga_preface]] for pp in pgsga_val_patterns] for x in y]
#pgsga_patterns = [pgsga_preface + val for val in pgsga_val_patterns]

# to avoid clashes with the surname 'ng'
feeding_tube_exclusion = [[{"LOWER": {"IN": ["dr", "mr", "mrs"]}}, {"IS_PUNCT": True, "OP": "?"}]]

feeding_tube_patterns = [[{'LOWER': 'g'}, {'TEXT': '-', 'OP': '?'}, {'LOWER': 'tube'}],
                        [{"LOWER": {"IN": ['i', 'r']}},
                         {"LOWER": {"IN": ['/']}},
                         {"LOWER": {"IN": ['o']}},
                         {"LOWER": {"IN": ['peg', 'ngt', 'rig', 'pej']}}],
                        [{"LOWER": {"IN": ["dr", "mr", "mrs"]}, "OP": "?"},
                         {"LOWER": {"IN": ['peg', 'ngt', 'rig', 'pej', 'ng', 'ngf']}}],
                        [{"LOWER": {"IN": ['jj', 'tof', 'enteral', 'ng']}}, 
                         {"LOWER": {"IN": ['tube', 'feed', 'feeding', 'feeds']}}],
                        [{"LOWER": {"FUZZY2": 'nasogastric'}}, 
                         {'LOWER': 'tube', "OP": "?"}],
                        [{"LOWER": {"FUZZY2": {'IN': ['radiological', 'percutaneous', 'balloon', 'surgical']}}, "OP": '?'},
                         {"LOWER": {"FUZZY2": {'IN': ['inserted', 'endoscopic']}}, "OP": '?'},
                         {"LOWER": {"FUZZY2": {'IN': ['gastrostomy', 'jejunostomy']}}}]] 


unit_patterns = [[{"IS_DIGIT": True, "OP": "?"},
                  {"_":{"sci_not": True}, "OP": "?"},
                    {"TEXT": {"REGEX": units_regex}, "OP": "?"}, 
                    {"LOWER": {"IN": ["/", "per"]}}, # 100mg/mL, 10mg/100mL, 10 mg per L...
                    {"IS_DIGIT": True, "OP": "?"}, 
                    {"TEXT": {"REGEX": units_regex}}],
                    [{"IS_DIGIT": True, "OP": "?"}, 
                    {"_":{"sci_not": True}, "OP": "?"},
                    {"TEXT": {"REGEX": units_regex}}], # 20L, 50 mg
                    [{"_": {"kind": "decimal"}}, 
                    {"_":{"sci_not": True}, "OP": "?"}, 
                    {"TEXT": {"REGEX": units_regex}}],
                    [{"_": {"kind": "decimal"}}, 
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
                    [{"_": {"kind": "decimal"}}, 
                    {"_":{"sci_not": True}, "OP": "?"},
                    {"NORM": "unit_num"}, 
                    {"LOWER": {"IN": ["/", "per"]}}, 
                    {"NORM": "unit_denom"}],
                    [{"LOWER": "bmi"},
                    {"TEXT": {"IN": ['-', '=', '~', ':', '>', '<']}, "OP": "?"},
                    {"IS_DIGIT": True}],
                    [{"LOWER": "bmi"},
                    {"TEXT": {"IN": ['-', '=', '~', ':', '>', '<']}, "OP": "?"},
                    {"_": {"kind": "decimal"}}]] 
                
unit_val_patterns = [[{"IS_DIGIT": True}, {"_":{"kind": "scientific"}, "OP": "?"}],
                     [{"_": {'kind': "decimal"}}, {"_":{"kind": "scientific"}, "OP": "?"}], 
                     [{"LOWER": {"IN": ["zero", "o"]}}],
                     [{"_": {'kind': "date"}, 'LENGTH': 3}]]

unit_norm_patterns = [[{"IS_DIGIT": False,
                        "_": {"kind": {"NOT_IN": ["date", "scientific", "decimal"]}},
                        "LOWER": {"NOT_IN": ["zero", "o", '-', '=', '~', ':', '>', '<']}}]]

unit_exclusion_patterns = [[{'LOWER': 'g'}, {'TEXT': '-', 'OP': '?'}, {'LOWER': 'tube'}]]        


ecog_exclusion = [{"TEXT": {"FUZZY": {"IN": ["karnofsky", "nodal", "nutrition", "receptor"]}}}]

ecog_preface = [
    {"LOWER": "ecog"}, 
    {"LOWER": {"IN": ["performance", "status", "ps"]}, "OP": "?"}, 
    {"LOWER": {"IN": ["score", "status", "borderline"]}, "OP": "?"}, 
    {"LOWER": {"IN": ["is", "now", "=", "still", "of", "~", "currently", "has", "remains", "between", "around", "normally", "was", "improved"]}, "OP": "?"}, \
    {"LOWER": {"IN": ["been", "at","to", "was"]}, "OP": "?"}, 
    {"LOWER": {"IN": ["least"]}, "OP": "?"}, 
    {"IS_PUNCT": True, "OP": "?"}
]

ps_preface = [
    {"LOWER": {"IN": ["performance", "status", "ps"]}}, 
    {"LOWER": {"IN": ["score", "status", "borderline"]}, "OP": "?"}, 
    {"LOWER": {"IN": ["is", "now", "=", "still", "of", "~", "currently", "has", "remains", "normally", "was", "improved"]}, "OP": "?"}, \
    {"LOWER": {"IN": ["been", "at","to", "was"]}, "OP": "?"}, 
    {"LOWER": {"IN": ["least"]}, "OP": "?"}, 
    {"IS_PUNCT": True, "OP": "?"}
]

ecog_backhalf = [
    [
      {"LOWER": {"IN": ["o", "zero", "0", "1", "2", "3", "4"]}}
    ],
    [
      {"IS_DIGIT": True}, 
      {"LOWER": {"IN": ["=", "/", "to", "and", "now"]}}, 
      {"IS_DIGIT": True}
    ], 
    [{"_": {'decimal': True}}], 
    [{"_": {'range': True}}]
]

ecog_patterns = [ecog_preface + pattern for pattern in ecog_backhalf] + \
                [ps_preface + pattern for pattern in ecog_backhalf] + \
                [ecog_exclusion + ps_preface + pattern for pattern in ecog_backhalf]


genomic_variants = [
    [
        {"LOWER": "egfr"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": {"IN": ["g", "c","l","t"]}},
        {"IS_DIGIT": True},
        {"LOWER": {"IN": ["x", "s","r","m"]}},
    ],
    [
        {"LOWER": "kras"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "g"},
        {"IS_DIGIT": True},
        {"LOWER": {"IN": ["c", "d", "v"]}},
    ],
    [
        {"LOWER": "eml"},
        {"IS_DIGIT": True},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "alk"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "fusion"},
    ],
    [
        {"LOWER": "alk"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": {"IN": ["g", "l"]}},
        {"IS_DIGIT": True},
        {"LOWER": {"IN": ["a", "r", "m"]}},
    ],
    [
        {"LOWER": "cd"},
        {"IS_DIGIT": True},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "ros"},
        {"IS_DIGIT": True},
    ],
    [
        {"LOWER": "ezr"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "ros"},
        {"IS_DIGIT": True},
    ],
    [
        {"LOWER": "sdc"},
        {"IS_DIGIT": True},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "ros"},
        {"IS_DIGIT": True},
    ],
    [
        {"LOWER": "slc"},
        {"IS_DIGIT": True},
        {"LOWER": "a"},
        {"IS_DIGIT": True},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "ros"},
        {"IS_DIGIT": True},
    ],
    [
        {"LOWER": "braf"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "g"},
        {"IS_DIGIT": True},
        {"LOWER": "a"},
    ],
    [
        {"LOWER": "braf"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "v"},
        {"IS_DIGIT": True},
        {"LOWER": "e"},
    ],
    [
        {"LOWER": "met"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": "exon"},
        {"IS_PUNCT": True, "OP": "?"},
        {"IS_DIGIT": True},
    ],
    [
        {"LOWER": "egfr"},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": {"IN": ["e"]}},
        {"IS_DIGIT": True},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": {"IN": ["a"]}},
        {"IS_DIGIT": True},
        {"IS_PUNCT": True, "OP": "?"},
        {"LOWER": {"IN": ["del"]}},
    ],
]

  # ecog_patterns = [# rare but occasional ecog 2.5
  #                    # ecog_preface + [{"_": {'kind': "decimal"}}], 
  #                     # special case for when ECOG of 0 is entered as ECOG of O (letter o instead of zero) or written in full
  #                     ecog_preface + [{"LOWER": {"IN": ["o", "zero", "0", "1", "2", "3", "4"]}}], 
  #                     # matches additional forms with range e.g. between 1 and 2, 1 to 2
  #                     ecog_preface + [{"IS_DIGIT": True}, 
  #                                     {"LOWER": {"IN": ["=", "-", "/", "to", "and", "now"]}}, 
  #                                     {"IS_DIGIT": True}], 
  #                     # special case to handle the fact that retokenisation may merge ranges if of the form 1-2 if they meet criteria for date entity
  #                 #    ecog_preface + [{"_": {'kind': "date"}, 'LENGTH': 3}],
  #                     # repeat the above except performance status 2, ps=2 without leading 'ecog'
  #                     # ps_preface + [{"IS_DIGIT": True}],
  #                 #    ps_preface + [{"_": {'kind': "decimal"}}], 
  #                     ps_preface + [{"LOWER": {"IN": ["o", "zero",  "0", "1", "2", "3", "4"]}}], 
  #                     ps_preface + [{"IS_DIGIT": True}, \
  #                                     {"LOWER": {"IN": ["=", "-", "/", "to", "and", "now"]}}, 
  #                                     {"IS_DIGIT": True}], 
  #                #     ps_preface + [{"_": {'kind': "date"}, 'LENGTH': 3}],
  #                     # repeat the above except with the exclusion token target
  #                     ecog_exclusion + ps_preface + [{"IS_DIGIT": True}],
  #                 #    ecog_exclusion + ps_preface + [{"_": {'kind': "decimal"}}], 
  #                     ecog_exclusion + ps_preface + [{"LOWER": {"IN": ["o", "zero"]}}], 
  #                     ecog_exclusion + ps_preface + [{"IS_DIGIT": True}, \
  #                                                 {"LOWER": {"IN": ["=", "-", "/", "to", "and", "now"]}}, 
  #                                                 {"IS_DIGIT": True}]]#, 
  #                #     ecog_exclusion + ps_preface + [{"_": {'kind': "date"}, 'LENGTH': 3}]]

# to match just the numeric portion within an ECOG status entity
ecog_val_patterns = [[{"TEXT": {"IN": ['0','1','2','3','4']}}], 
                     [{"LOWER": {"IN": ["zero", "o"]}}]]#,
                    # [{"_": {"decimal": True}}]]
                        #[{"_": {'date': True}, 'LENGTH': 3}]]