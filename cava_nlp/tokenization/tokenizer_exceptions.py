# type: ignore
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

# create special cases for cancer staging
for stage in stage_exceptions:
    special_cases.append([stage, [{ORTH: stage, NORM: 'stage'}]])

# other special cases for cancer-specific vocabulary
for term in special_vocab:
    special_cases.append([term, [{ORTH: term, NORM: 'cava_term'}]])