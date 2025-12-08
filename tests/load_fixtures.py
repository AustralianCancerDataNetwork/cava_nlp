import csv
import ast
import os


def parse_token_list(raw):
    """
    Parse a CSV "Expected Tokens" or "Expected Result" field.
    Handles:
        - [a, b, c]
        - ['a','b','c']
        - COMM → ','
        - LF → '\n'
        - Properly quoted output for ast.literal_eval
    """
    cleaned = raw.strip()

    if not (cleaned.startswith("[") and cleaned.endswith("]")):
        raise ValueError(f"Token list must be bracketed: {raw}")

    inner = cleaned[1:-1].strip()

    # Nothing inside?
    if not inner:
        return []

    # Already quoted? → eval directly
    if any(q in inner for q in ("'", '"')):
        return ast.literal_eval(f"[{inner}]")

    # Otherwise: bare tokens → quote each
    raw_tokens = [t.strip() for t in inner.split(",")]

    processed = []
    for tok in raw_tokens:
        if tok == "COMM":
            processed.append("','")
        elif tok == "LF":
            processed.append("'\\n'")
        else:
            processed.append(f"'{tok}'")

    list_str = "[" + ", ".join(processed) + "]"
    return ast.literal_eval(list_str)

def load_csv_rows(filename, skip_empty_field="Input Data"):
    """
    Generic CSV loader for both tokenisation and normalisation tests.
    """
    fixtures_path = os.path.join(os.path.dirname(__file__), filename)

    rows = []
    with open(fixtures_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if skip_empty_field and not row[skip_empty_field].strip():
                continue
            rows.append(row)
    return rows
