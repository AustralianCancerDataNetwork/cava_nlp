year_regex = r'(^(19|20)\d\d$|^\d?\d$)'
numeric_month_regex = r'(^[0-1]?\d$)'
day_regex = r'(^[0-3]?\d$)'
months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec',
          'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
#ordinal = '\d{1,2}(?:[stndrh]){2}?'
ordinal = '^([stndrh]{2})$'

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

scientific_notation = r'^x?10\^\d+$'
times = ['am', 'a.m.', 'a.m', 'pm', 'p.m.', 'p.m', 'hrs', 'hr', 'o\'clock', 'oclock']
# emails = r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9]+(\.[A-Za-z]{2,3})+' - this version caused catastrophic backtracking on long strings
emails = r'\w+(?:[.-]\w+)*@\w+(?:[.-]\w+)*(?:\.\w{2,3})+'

# single alpha char with no whitespace to merge abbreviatons like p.o. or i.v.
abbv = r'^[a-zA-Z]$'
# alpha string of arbitrary length with no whitespace as 2nd part of abbreviations like o/night b'fast 
no_whitespace = r'^[a-zA-Z]+$'

weight_units = ['kg', 'kilo', 'kilos', 'g', 'gr', 'kilogram', 'kilograms', 'kgs', 
                'BMI', 'bmi', 'lb', 'lbs', 'pounds', 'KG','Kg', 'kG']


# added special cases to capture units with a slash in the middle
units_num = ['mg', 'mcg', 'g', 'units', 'u', 'mgs', 'mcgs', 'gram', 'grams', 'mG', 'mL', 'mol']
units_denom = ['mg', 'mgc', 'g', 'kg', 'ml', 'l', 'm2', 'm^2', 'hr', 'liter', 'gram', 'L', 'mL', 'KG', 'MG',
               'mG', 'kG', 'kilogram', 'lb', 'pounds', 'lbs', 'kilos', 'Kg']
unit_suffix = []

for a in units_num:
    for b in units_denom:
        if a != b:
            #special_cases.append([f'{a}/{b}', [{ORTH: a, NORM: 'unit_num'}, {ORTH: '/'}, {ORTH: b, NORM: 'unit_denom'}]])
            unit_suffix.append(f'{a}/{b}')

units_regex = '|'.join([f'{u}' for u in units_denom])
#units_regex = rf'^({units_regex})$'
