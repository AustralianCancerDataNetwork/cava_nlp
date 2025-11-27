import csv
import ast
import pytest
import os
from cava_nlp import CaVaLang
from spacy.language import Language
from cava_nlp.normalisation.normaliser import ClinicalNormalizer
from .load_fixtures import parse_token_list, load_csv_rows

from dataclasses import dataclass

@dataclass
class NormalizationTestCase:
    name: str
    input: str
    expected_tokens: list[str]
    expected_norms: dict
    expected_ext: dict
    doc: object  # processed spaCy Doc to avoid re-handling

@pytest.fixture(scope="session")
def nlp():
    n = CaVaLang()
    n.add_pipe("clinical_normalizer", first=True)
    return n

@pytest.fixture(params=load_csv_rows("normalisation_fixtures.csv"))
def scenario(request, nlp):
    row = request.param

    name = row["Test Case"]
    input_text = row["Input Data"]

    expected_tokens = parse_token_list(row["Expected Tokens"])

    norm_raw = row["Expected Norms"].strip()
    expected_norms = ast.literal_eval(norm_raw) if norm_raw and norm_raw != "{}" else {}

    ext_raw = row["Expected Extensions"].strip()
    expected_ext = ast.literal_eval(ext_raw) if ext_raw and ext_raw != "{}" else {}

    doc = nlp(input_text)

    return NormalizationTestCase(
        name=name,
        input=input_text,
        expected_tokens=expected_tokens,
        expected_norms=expected_norms,
        expected_ext=expected_ext,
        doc=doc,
    )

def test_tokens_from_csv(scenario):
    actual_tokens = [t.text.replace("\r\n", "\n") for t in scenario.doc]

    assert actual_tokens == scenario.expected_tokens, (
        f"\nFAILED TOKEN MERGE: {scenario.name}\n"
        f"INPUT:       {scenario.input!r}\n"
        f"EXPECTED:    {scenario.expected_tokens}\n"
        f"ACTUAL:      {actual_tokens}\n"
    )

def test_norms_from_csv(scenario):
    actual_norms = {
        t.text: t.norm_
        for t in scenario.doc
        if (t.norm_ != t.text and t.norm_ != t.text.lower())
    }

    assert actual_norms == scenario.expected_norms, (
        f"\nFAILED NORM VALUES: {scenario.name}\n"
        f"INPUT:       {scenario.input!r}\n"
        f"EXPECTED:    {scenario.expected_norms}\n"
        f"ACTUAL:      {actual_norms}\n"
    )

def test_extensions_from_csv(scenario):
    actual_ext = {}

    for t in scenario.doc:
        if t.text in scenario.expected_ext:
            actual_ext[t.text] = {}
            exp = scenario.expected_ext[t.text]

            if "kind" in exp:
                actual_ext[t.text]["kind"] = t._.kind

            if "value" in exp:
                actual_ext[t.text]["value"] = t._.value

    assert actual_ext == scenario.expected_ext, (
        f"\nFAILED EXTENSION VALUES: {scenario.name}\n"
        f"INPUT:       {scenario.input!r}\n"
        f"EXPECTED:    {scenario.expected_ext}\n"
        f"ACTUAL:      {actual_ext}\n"
    )


# @pytest.mark.parametrize(
#     "test_name,input_text,expected_tokens_raw,expected_norms_raw",
#     [
#         (
#             row["Test Case"],
#             row["Input Data"],
#             row["Expected Tokens"],
#             row["Expected Norms"],
#         )
#         for row in load_csv_rows("normalisation_fixtures.csv")
#     ]
# )
# def test_clinical_normalizer_from_csv(
#     nlp, test_name, input_text, expected_tokens_raw, expected_norms_raw, expected_ext_raw
# ):

#     doc = nlp(input_text)

#     # Expected tokens
#     expected_tokens = parse_token_list(expected_tokens_raw)
#     actual_tokens = [t.text.replace("\r\n", "\n") for t in doc]

#     # Expected norms (simple dict literal)
#     norm_raw = expected_norms_raw.strip()
#     if not norm_raw or norm_raw == "{}":
#         expected_norms = {}
#     else:
#         try:
#             expected_norms = ast.literal_eval(norm_raw)
#             if not isinstance(expected_norms, dict):
#                 raise ValueError
#         except Exception:
#             raise ValueError(
#                 f"Invalid Expected Norms format: {expected_norms_raw!r}"
#             )

#     actual_norms = {
#         t.text: t.norm_
#         for t in doc
#         if (t.norm_ != t.text and t.norm_ != t.text.lower())
#     }

#     ext_raw = expected_ext_raw.strip()
#     if not ext_raw or ext_raw == "{}":
#         expected_ext = {}
#     else:
#         expected_ext = ast.literal_eval(ext_raw)

#     actual_ext = {}
#     for t in doc:
#         if t.text in expected_ext:
#             actual_ext[t.text] = {}
#             if "kind" in expected_ext[t.text]:
#                 actual_ext[t.text]["kind"] = t._.kind
#             if "value" in expected_ext[t.text]:
#                 actual_ext[t.text]["value"] = t._.value

#     assert actual_ext == expected_ext, (
#         f"\nFAILED EXTENSION VALUES: {test_name}\n"
#         f"INPUT:       {input_text!r}\n"
#         f"EXPECTED:    {expected_ext}\n"
#         f"ACTUAL:      {actual_ext}\n"
#     )

#     assert actual_tokens == expected_tokens, (
#         f"\nFAILED TOKEN MERGE: {test_name}\n"
#         f"INPUT:       {input_text!r}\n"
#         f"EXPECTED:    {expected_tokens}\n"
#         f"ACTUAL:      {actual_tokens}\n"
#     )

#     assert actual_norms == expected_norms, (
#         f"\nFAILED NORM VALUES: {test_name}\n"
#         f"INPUT:       {input_text!r}\n"
#         f"EXPECTED:    {expected_norms}\n"
#         f"ACTUAL:      {actual_norms}\n"
#     )

