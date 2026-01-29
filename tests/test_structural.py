import csv
import ast
import pytest
import os
from cava_nlp import CaVaLang
from spacy.language import Language
from cava_nlp.structural.document_layout import DocumentLayout


from dataclasses import dataclass

from tests.test_entities import nlp
@pytest.fixture(scope="session")
def nlp_structural():
    n = CaVaLang()
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