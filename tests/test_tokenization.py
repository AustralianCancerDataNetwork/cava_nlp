import csv
import ast
import pytest
import os
from cava_nlp import CaVaLang

from .load_fixtures import parse_token_list, load_csv_rows


# def load_tokenization_fixtures():
#     """Load tokenization_fixtures.csv and return list of test rows."""


#     rows = []
#     with open(fixtures_path, newline="", encoding="utf-8-sig") as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             # skip blank lines
#             if not row["Input Data"].strip():
#                 continue
#             rows.append(row)
#     return rows

#     fixtures_path = os.path.join(
#         os.path.dirname(__file__),
#         "tokenization_fixtures.csv"
#     )

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


# @pytest.mark.parametrize(
#     "test_name,input_text,expected_raw",
#     [
#         (row["Test Case"], row["Input Data"], row["Expected Result"])
#         for row in load_tokenization_fixtures()
#     ]
# )
# def test_tokenizer_from_csv(test_name, input_text, expected_raw):
#     """
#     Generic test runner for all CSV-driven tokenization tests.
#     """
#     # Create CaVaLang with default tokenizer + medspaCy
#     nlp = CaVaLang()

#     # Parse expected token list from CSV string using ast.literal_eval
#     # Expected format: "[hello, how]" or "['hello','how']"
#     # Fix missing quotes around tokens (CSV gives bare words)
#     cleaned = expected_raw.strip()

#     # Put quotes around tokens if they aren't quoted
#     if cleaned.startswith("[") and cleaned.endswith("]"):
#         inner = cleaned[1:-1].strip()

#         if inner:
#             # Case 1: If already quoted → do nothing
#             if not any(q in inner for q in ("'", '"')):
#                 # Tokenize manually: split on commas, but preserve literal ',' tokens
#                 raw_tokens = [t.strip() for t in inner.split(",")]

#                 tokens = []
#                 for tok in raw_tokens:
#                     if tok == "COMM":  
#                         # literal comma token → represented as ','
#                         tokens.append("','")
#                     elif tok == "LF":
#                         tokens.append("'\\n'")
#                     else:
#                         tokens.append(f"'{tok}'")

#                 inner = ", ".join(tokens)

#         cleaned = f"[{inner}]"


#     try:
#         expected = ast.literal_eval(cleaned)
#     except Exception as e:
#         raise ValueError(f"Cannot parse Expected Result: {expected_raw}\nCleaned: {cleaned}") from e

#     doc = nlp(input_text)

#     actual = [t.text.replace('\r\n', '\n') for t in doc]

#     assert actual == expected, (
#         f"\nFAILED CASE: {test_name}\n"
#         f"INPUT:      {input_text!r}\n"
#         f"EXPECTED:   {expected}\n"
#         f"ACTUAL:     {actual}\n"
#     )
