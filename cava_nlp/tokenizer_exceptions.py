import re
from spacy.symbols import ORTH, NORM

from ._tokenizer_exceptions_list import stage_exceptions, special_vocab

special_cases = [
    ['??', [{ORTH: '??', NORM: 'query'}]],
    ['???', [{ORTH: '???', NORM: 'query'}]],
    ['+++', [{ORTH: '+++', NORM: 'extreme_positive'}]],
    ['++', [{ORTH: '++', NORM: 'very_positive'}]],
    ['+ve', [{ORTH: '+ve', NORM: 'positive'}]],
    ['+', [{ORTH: '+', NORM: 'positive'}]],
    ['pos', [{ORTH: 'pos', NORM: 'positive'}]],
    ['<-->', [{ORTH: '<-->', NORM: 'both_arrow'}]],
    ['<->', [{ORTH: '<->', NORM: 'both_arrow'}]],
    ['-->', [{ORTH: '-->', NORM: 'right_arrow'}]],
    ['<--', [{ORTH: '<--', NORM: 'left_arrow'}]],
    ['--', [{ORTH: '--', NORM: 'decrease'}]],
    ['-ve', [{ORTH: '-ve', NORM: 'negative'}]],
    ['neg', [{ORTH: 'neg', NORM: 'negative'}]],
    # spacy defaults already have a.m. and p.m. special cases - we allow for missing final dots
    ['a.m', [{ORTH: 'a.m', NORM: 'a.m.'}]],
    ['p.m', [{ORTH: 'p.m', NORM: 'p.m.'}]],
]

# added special cases to capture units with a slash in the middle
units_num = ['mg', 'mcg', 'g', 'units', 'u', 'mgs', 'mcgs', 'gram', 'grams', 'mG', 'mL', 'mol']
units_denom = ['mg', 'mgc', 'g', 'kg', 'ml', 'l', 'm2', 'm^2', 'hr', 'liter', 'gram', 'L', 'mL', 'KG', 'mG', 'kG']
unit_suffix = []

for a in units_num:
    for b in units_denom:
        if a != b:
            special_cases.append([f'{a}/{b}', [{ORTH: a, NORM: 'unit_num'}, {ORTH: '/'}, {ORTH: b, NORM: 'unit_denom'}]])
            unit_suffix.append(f'{a}/{b}')

units_regex = '|'.join([f'{u}' for u in units_denom])
units_regex = f'^(\d+)?({units_regex})$'

year_regex = '(^(19|20)\d\d$|^\d?\d$)'
numeric_month_regex = '(^[0-1]?\d$)'
day_regex = '(^[0-3]?\d$)'
months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec',
          'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
#ordinal = '\d{1,2}(?:[stndrh]){2}?'
ordinal = '^([stndrh]{2})$'
scientific_notation = '^x?10\^\d+$'
times = ['am', 'a.m.', 'a.m', 'pm', 'p.m.', 'p.m']
# single alpha char with no whitespace to merge abbreviatons like p.o. or i.v.
abbv = r'^[a-zA-Z]$'
# alpha string of arbitrary length with no whitespace as 2nd part of abbreviations like o/night b'fast 
no_whitespace = r'^[a-zA-Z]+$'
# email regex
emails = r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9]+(\.[A-Za-z]{2,3})+'

# create special cases for cancer staging
for stage in stage_exceptions:
    special_cases.append([stage, [{ORTH: stage, NORM: 'stage'}]])

# other special cases for cancer-specific vocabulary
for term in special_vocab:
    special_cases.append([term, [{ORTH: term, NORM: 'cava_term'}]])