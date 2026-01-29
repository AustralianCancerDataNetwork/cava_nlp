import pytest
import spacy
from cava_nlp import CaVaLang  
from cava_nlp.context.hooks import enable_context
from cava_nlp.rule_engine import RuleEngine
from cava_nlp.structural.document_layout import DocumentLayout


@pytest.fixture()
def nlp_with_context():
    n = CaVaLang()
    n.add_pipe("clinical_normalizer")
    n.add_pipe("document_layout") 
    n.add_pipe(
        "rule_engine",
        name="ecog_value",
        config={
            "engine_config_path": None,      
            "component_name": "ecog_status",   
        },
    )
    n.add_pipe(
        "rule_engine",
        name="variants_of_interest", 
        config={
                "engine_config_path": None,
                "component_name": "variants_of_interest",
        }
    )
    enable_context(n)
    n.add_pipe("resolve_closest_context", last=True)
    return n

@pytest.fixture()
def nlp_with_tests_context():
    n = CaVaLang()
    n.add_pipe("clinical_normalizer")
    n.add_pipe("document_layout") 
    n.add_pipe(
        "rule_engine",
        name="variants_of_interest",
        config={
            "engine_config_path": None,
            "component_name": "variants_of_interest",
        },
    )
    enable_context(n, profile="tests")
    n.add_pipe("resolve_closest_context", last=True)
    return n


def test_context_sets_default_span_attributes(nlp_with_context):
    doc = nlp_with_context("is currently ECOG 2")

    spans = list(doc.ents)
    assert spans  

    assert any(
        getattr(span._, "is_current", False)
        for span in spans
    )

def test_genomic_results_basic(nlp_with_tests_context):
    doc = nlp_with_tests_context(
        "KRAS detected\nEGFR-\nALK results pending\nPDL1 (high)"
    )

    ents = {ent.text: ent for ent in doc.ents}

    assert ents["KRAS"]._.is_positive is True
    assert ents["EGFR"]._.is_negated is True
    assert ents["ALK"]._.is_unconfirmed is True
    assert ents["PDL1"]._.is_positive is True

def test_bullet_list_does_not_trigger_negation(nlp_with_tests_context):
    doc = nlp_with_tests_context(
        "- KRAS detected\n"
        "- EGFR detected\n"
        "- ALK pending"
    )

    ents = {ent.text: ent for ent in doc.ents}

    assert ents["KRAS"]._.is_positive is True
    assert ents["EGFR"]._.is_positive is True
    assert ents["ALK"]._.is_unconfirmed is True

    # Explicitly ensure bullet hyphens didn't negate
    assert not ents["KRAS"]._.is_negated
    assert not ents["EGFR"]._.is_negated

def test_multiple_genomic_results_do_not_bleed(nlp_with_tests_context):
    doc = nlp_with_tests_context(
        "EGFR negative\n"
        "KRAS detected\n"
        "ALK pending\n"
        "BRAF undetectable"
    )

    ents = {ent.text: ent for ent in doc.ents}

    assert ents["EGFR"]._.is_negated is True
    assert ents["KRAS"]._.is_positive is True
    assert ents["ALK"]._.is_unconfirmed is True
    assert ents["BRAF"]._.is_negated is True

def test_pending_only_applies_to_correct_target(nlp_with_tests_context):
    doc = nlp_with_tests_context(
        "ALK results pending\nKRAS detected"
    )

    ents = {ent.text: ent for ent in doc.ents}

    assert ents["ALK"]._.is_unconfirmed is True
    assert ents["KRAS"]._.is_positive is True
    assert not ents["KRAS"]._.is_unconfirmed


def test_termination_on_newline(nlp_with_tests_context):
    doc = nlp_with_tests_context(
        "EGFR negative\nKRAS detected"
    )

    ents = {ent.text: ent for ent in doc.ents}

    assert ents["EGFR"]._.is_negated is True
    assert ents["KRAS"]._.is_positive is True

def test_dash_only_negates_when_attached(nlp_with_tests_context):
    doc = nlp_with_tests_context(
        "EGFR-\n- KRAS detected"
    )

    ents = {ent.text: ent for ent in doc.ents}

    assert ents["EGFR"]._.is_negated is True
    assert ents["KRAS"]._.is_positive is True


def test_overlapping_modifier_is_rejected(nlp_with_tests_context):
    doc = nlp_with_tests_context("PDL-1 (high)")

    pdl1 = next(
        ent for ent in doc.ents
        if ent.text.lower().startswith("pdl-1")
    )
    assert pdl1 is not None
    assert pdl1._.is_positive is True
    # the hyphen should not cause negation
    assert not getattr(pdl1._, "is_negated", False)

def test_attached_minus_single_token(nlp_with_tests_context):
    doc = nlp_with_tests_context("EGFR-")
    egfr = doc[0:1]
    assert egfr._.is_negated is True


def test_attached_minus_slash_chain(nlp_with_tests_context):
    doc = nlp_with_tests_context("KRAS/ALK-")
    kras = doc[0:1]
    alk = doc[2:3]

    assert kras._.is_negated is True
    assert alk._.is_negated is True

def test_attached_plus_slash_chain(nlp_with_tests_context):
    doc = nlp_with_tests_context("KRAS/ALK+")
    kras = doc[0:1]
    alk = doc[2:3]

    assert kras._.is_positive is True
    assert alk._.is_positive is True