from .numeric import ordinal

year_regex = r'(^(19|20)\d\d$|^\d{2}$)'
numeric_month_regex = r'(^[0-1]?\d$)'
day_regex = r'(^[0-3]?\d$)'
months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec',
          'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december']

date_patterns = [[{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "-", "SPACY": False}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20 - keep as digit based because 3 part unlikely to be false pos 
                 [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "-", "SPACY": False}, {"IS_DIGIT": True}, {"IS_DIGIT": True}, {"ORTH": ":", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": ":", "SPACY": False}, {"IS_DIGIT": True}], # 1/1/20, 1-1-20 with times HH:MM:SS
                 [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "/", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": "/", "SPACY": False}, {"IS_DIGIT": True}], # no longer expressed as 'in', as we really want the separators to be the same
                 [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": ".", 'SPACY': False}, {"IS_DIGIT": True, 'SPACY': False},  {"ORTH": ".", "SPACY": False}, {"IS_DIGIT": True}], 
                 [{"TEXT": {"REGEX": numeric_month_regex}, 'SPACY': False},  {"ORTH": {"IN": ["/", "-"]}, 'SPACY': False}, {"TEXT": {"REGEX": year_regex}}], # 1/2020, 1-2020 - changed from is digit to avoid false pos with BP
                 # [{"TEXT": {"REGEX": day_regex}, 'SPACY': False},  {"ORTH": {"IN": ["/", "-"]}, 'SPACY': False}, {"TEXT": {"REGEX": numeric_month_regex}}], # 31/12 - removed as too many false pos with measurements like 12/8 and ranges like 0-1, also limited utility of relative dates
                 [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "/", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": "/", "SPACY": False}, {"TEXT": {"REGEX": year_regex}}], # 1-Jan-20, 1/jan/20
                 [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": "-", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": "-", "SPACY": False}, {"TEXT": {"REGEX": year_regex}}], # no longer expressed as 'in', as we really want the separators to be the same
                 [{"IS_DIGIT": True, 'SPACY': False}, {"ORTH": ".", 'SPACY': False}, {"LOWER": {"IN": months}},  {"ORTH": ".", "SPACY": False}, {"TEXT": {"REGEX": year_regex}}], 
                 [{"IS_DIGIT": True, 'OP': "?"}, {"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": numeric_month_regex}}, {"TEXT": {"REGEX": ordinal}}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}], # September 4th
                 [{"IS_DIGIT": True, 'OP': "?"}, {"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": year_regex}}], # Jan/2020, Jan 2020, Jan '20
                 [{"IS_DIGIT": True, 'OP': "?"}, {"LOWER": {"IN": months}},  {"ORTH": {"IN": ["/", "-", "\'"]}, "OP": "?", "SPACY": False}, {"TEXT": {"REGEX": numeric_month_regex}}, {"TEXT": {"REGEX": year_regex}, "OP": "?"}]] # September 4th

times = ['am', 'a.m.', 'a.m', 'pm', 'p.m.', 'p.m', 'hrs', 'hr', 'o\'clock', 'oclock']


