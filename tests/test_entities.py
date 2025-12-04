import csv
import ast
import pytest
import os
from cava_nlp import CaVaLang
from spacy.language import Language
from cava_nlp.normalisation.normaliser import ClinicalNormalizer
from .load_fixtures import parse_token_list, load_csv_rows
from dataclasses import dataclass
from cava_nlp.rule_engine import RuleEngine

@dataclass
class RuleEngineTestCase:
    name: str
    input: str
    expected_entities: dict
    test_pipes: list[str]
    expected_attributes: dict
    doc: object  # processed spaCy Doc to avoid re-handling

@pytest.fixture(scope="session")
def nlp():
    n = CaVaLang()
    n.add_pipe("clinical_normalizer", first=True)
    # todo: iterate csv and pull in all in-scope rule engines to validate
    n.add_pipe(
        "rule_engine",
        name="ecog_value",
        config={
            "engine_config_path": None,       # loading and testing default rule engine only
            "component_name": "ecog_status",   
        },
    )
    n.add_pipe(
        "rule_engine",
        name="variants_of_interest",
        config={
            "engine_config_path": None,       # loading and testing default rule engine only
            "component_name": "variants_of_interest",   
        },
    )
    return n

@pytest.fixture(params=load_csv_rows("entity_fixtures.csv"))
def scenario(request, nlp):
    row = request.param

    name = row["Test Case"]
    input_text = row["Input Data"]

    ent_raw = row["Expected Entities"].strip()
    try:
        expected_entities = ast.literal_eval(ent_raw) if ent_raw and ent_raw != "{}" else {}
    except Exception as e:
        print(f"Error parsing Expected Entities in test case {name}: {e}")
    
    test_pipes = list(expected_entities.values())
    attr_raw = row["Entity Attributes"].strip()
    expected_attributes = ast.literal_eval(attr_raw) if attr_raw and attr_raw != "{}" else {}
    xfail_raw = row.get("XFail", "").strip().lower()
    xfail = xfail_raw in ("1", "true", "yes", "xfail")
    request.applymarker(pytest.mark.xfail(reason=row["Test Case"])) if xfail else None
    doc = nlp(input_text)

    return RuleEngineTestCase(
        name=name,
        input=input_text,
        expected_entities=expected_entities,
        test_pipes=test_pipes,
        expected_attributes=expected_attributes,
        doc=doc
    )

def extract_ents(doc, label):
    return {sp: sp.label_ for sp in doc.ents if sp.label_==label}

def test_rule_engine_from_csv(scenario):
    sc = scenario
    for pipe in sc.test_pipes:
        spans = extract_ents(sc.doc, pipe)
        entities = {k.text: v for k, v in spans.items()}
        assert entities == {k: v for k, v in sc.expected_entities.items() if v == pipe}, (
            f"\nFAILED ENTITY EXTRACTION: {sc.name} (pipe: {pipe})\n"
            f"INPUT:       {sc.input!r}\n"
            f"EXPECTED:    { {k: v for k, v in sc.expected_entities.items() if v == pipe} }\n"
            f"ACTUAL:      {spans}\n"
        )

    for attr, expected_attr in sc.expected_attributes.items():
        for span in sc.doc.spans.get(attr, []):
            expected_val = expected_attr.get(span.text)
            if expected_val:
                actual_val = getattr(span._, 'value')
                assert actual_val == expected_val, (
                    f"\nFAILED ATTRIBUTE CHECK: {sc.name} (pipe: {pipe}, entity: {span.text}, attr: {pipe})\n"
                    f"INPUT:       {sc.input!r}\n"
                    f"EXPECTED:    {expected_val}\n"
                    f"ACTUAL:      {actual_val}\n"
                )