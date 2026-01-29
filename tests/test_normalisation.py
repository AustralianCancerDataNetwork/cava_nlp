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
    n.add_pipe("clinical_normalizer")
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
    expected_ext = scenario.expected_ext
    actual_ext = {}

    for token in scenario.doc:
        text = token.text

        if text not in expected_ext:
            continue

        actual_ext[text] = {}

        for key, _ in expected_ext[text].items():

            try:
                val = getattr(token._, key)
            except Exception:
                val = None  

            actual_ext[text][key] = val

    assert actual_ext == expected_ext, (
        f"\nFAILED EXTENSION VALUES: {scenario.name}\n"
        f"INPUT:       {scenario.input!r}\n"
        f"EXPECTED:    {expected_ext}\n"
        f"ACTUAL:      {actual_ext}\n"
    )
