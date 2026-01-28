# type: ignore
from spacy.symbols import ORTH, NORM
from typing import Dict, List
from ._tokenizer_exceptions_list import stage_exceptions, special_vocab

TokenizerException = List[Dict[str, str]]
SpecialCase = tuple[str, TokenizerException]

special_cases: List[SpecialCase] = [
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
units_num: List[str] = ['mg', 'mcg', 'g', 'units', 'u', 'mgs', 'mcgs', 'gram', 'grams', 'mG', 'mL', 'mol']
units_denom: List[str] = ['mg', 'mgc', 'g', 'kg', 'ml', 'l', 'm2', 'm^2', 'hr', 'liter', 'gram', 'L', 'mL', 'KG', 
                          'mG', 'kG', 'kilogram', 'lb', 'pounds', 'lbs', 'kilos', 'Kg']
unit_suffix: List[str] = []

for a in units_num:
    for b in units_denom:
        if a != b:
            special_cases.append([f'{a}/{b}', [{ORTH: a, NORM: 'unit_num'}, {ORTH: '/'}, {ORTH: b, NORM: 'unit_denom'}]])
            unit_suffix.append(f'{a}/{b}')

units_regex = '|'.join([f'{u}' for u in units_denom])
units_regex = f'^(\\d+)?({units_regex})$'

def build_stage_exceptions() -> Dict[str, TokenizerException]:
    return {
        stage: [{ORTH: stage, NORM: "stage"}]
        for stage in stage_exceptions
    }


def build_special_vocab_exceptions() -> Dict[str, TokenizerException]:
    return {
        term: [{ORTH: term, NORM: "cava_term"}]
        for term in special_vocab
    }


def build_clinical_symbol_exceptions() -> Dict[str, TokenizerException]:
    exc = {}
    for case, rule in special_cases:
        exc[case] = rule
    return exc


# def build_unit_slash_exceptions():
#     return {
#         f"{a}/{b}": [
#             {ORTH: a, NORM: "unit_num"},
#             {ORTH: "/"},
#             {ORTH: b, NORM: "unit_denom"},
#         ]
#         for a in units_num
#         for b in units_denom
#         if a != b
#     }



def build_cycle_day_exceptions(max_cycle: int = 6, max_day: int = 21) -> Dict[str, TokenizerException]:
    """
    Build a list of cycle/day shorthand tokens used in oncology notes,
    such as c1d1, c2d7, etc.
    """

    tokens = [f'c{i}' for i in range(1, max_cycle + 1)]
    tokens += [f'C{i}' for i in range(1, max_cycle + 1)]

    for c in range(1, max_cycle + 1):
        for d in range(1, max_day + 1):
            lower = f"c{c}d{d}"
            tokens.append(lower)
            tokens.append(lower.upper())
    return {
        term: [{ORTH: term, NORM: "cycle_day"}]
        for term in tokens
    }
