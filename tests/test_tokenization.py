import csv
import ast
import pytest
import os
from cava_nlp import CaVaLang

from .load_fixtures import parse_token_list, load_csv_rows


@pytest.mark.parametrize(
    "test_name,input_text,expected_raw",
    [
        (row["Test Case"], row["Input Data"], row["Expected Result"])
        for row in load_csv_rows("tokenization_fixtures.csv")
    ]
)
def test_tokenizer_from_csv(test_name, input_text, expected_raw):

    nlp = CaVaLang()
    expected = parse_token_list(expected_raw)

    doc = nlp(input_text)
    actual = [t.text.replace("\r\n", "\n") for t in doc]

    assert actual == expected, (
        f"\nFAILED CASE: {test_name}\n"
        f"INPUT:      {input_text!r}\n"
        f"EXPECTED:   {expected}\n"
        f"ACTUAL:     {actual}\n"
    )

