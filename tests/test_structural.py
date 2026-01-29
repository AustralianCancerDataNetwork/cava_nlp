import csv
import ast
import pytest
import os
from cava_nlp import CaVaLang
from spacy.language import Language
from cava_nlp.structural.document_layout import DocumentLayout

from tests.test_entities import nlp
@pytest.fixture(scope="session")
def nlp_structural():
    n = CaVaLang()
    n.add_pipe("clinical_normalizer")
    n.add_pipe("document_layout")
    return n


def test_bullet_detection_ignores_whitespace(nlp_structural):
    doc = nlp_structural("  - KRAS detected\nEGFR negative")

    assert doc._.list_items
    start, end = doc._.list_items[0]
    assert doc[start:end].text.strip().startswith("-")


def test_parenthetical_and_bullet_coexist(nlp_structural):

    doc = nlp_structural("- PDL1 (high)\n- EGFR negative")

    assert doc._.parentheticals
    assert doc._.list_items
    assert len(doc._.parentheticals) == 1
    assert len(doc._.list_items) == 2

def test_bullet_not_mid_sentence(nlp_structural):
    doc = nlp_structural("KRAS - EGFR detected")
    assert not doc._.list_items

def test_multiple_parentheticals_single_sentence(nlp_structural):
    doc = nlp_structural("- PDL1 (high) (TPS > 50%)")

    assert len(doc._.parentheticals) == 2
    assert len(doc._.list_items) == 1

def test_nested_parentheticals(nlp_structural):
    doc = nlp_structural("- finding (level (high)) noted")

    spans = [doc[s:e].text for s, e in doc._.parentheticals]
    assert "(level (high))" in spans
