import spacy, pytest
from cava_nlp import CaVaLang  
from cava_nlp.tokenization.exceptions import (
    build_stage_exceptions,
    build_special_vocab_exceptions,
    build_clinical_symbol_exceptions
)

def test_language_registered():
    nlp = spacy.blank("cava_lang")
    assert nlp.lang == "cava_lang"

def test_email_masking(processed_doc):
    text = processed_doc.text
    assert "@" not in text
    assert "xxxxx" in text  # masked with repeated x's

def test_whitespace_collapse(nlp_cava):
    doc = nlp_cava("Hello   world")
    assert doc.text == "Hello world"

@pytest.mark.parametrize("text,norm", [
    ("+++", "extreme_positive"),
    ("++", "very_positive"),
    ("+ve", "positive"),
    ("-ve", "negative"),
    ("neg", "negative"),
])
def test_clinical_symbol_exceptions(nlp_cava, text, norm):
    doc = nlp_cava(text)
    assert len(doc) == 1
    assert doc[0].norm_ == norm


def test_stage_exception_list(nlp_cava):
    exc = build_stage_exceptions().keys()
    for stage in list(exc):
        doc = nlp_cava(stage)
        assert len(doc) == 1

@pytest.mark.parametrize("text", ["o'clock"])
def test_special_vocab_exceptions(nlp_cava, text):
    doc = nlp_cava(text)
    assert len(doc) == 1
    assert doc[0].norm_ == "cava_term"


def test_unit_slash_exceptions(nlp_cava):
    doc = nlp_cava("mg/kg")
    assert [t.text for t in doc] == ["mg", "/", "kg"]
    assert doc[0].norm_ == "unit_num"
    assert doc[2].norm_ == "unit_denom"

def test_prefix_suffix_pruning():
    from cava_nlp.tokenization.builder import build_cava_prefixes, build_cava_suffixes

    prefixes = build_cava_prefixes()
    suffixes = build_cava_suffixes()

    # We *should* have these brutal prefix/suffix rules
    assert ":" in prefixes
    assert "-" in suffixes

    # But NO emoji or weird English defaults
    assert all(not p.startswith("::") for p in prefixes) # type: ignore


def test_drop_single_letter_english_abbrev(nlp_cava):
    doc = nlp_cava("p.")
    assert [t.text for t in doc] == ["p", "."]


def test_url_not_treated_as_single_token(nlp_cava):
    doc = nlp_cava("Visit http://example.com now.")
    assert len(doc) > 3  # should be split apart


@pytest.mark.parametrize("text", [
    "mg/kg",
    "ECOG 1",
    "HER2 positive",
    "01/02/2024",
    "70kg",
    "WBC 1e3",
])
def test_roundtrip(nlp_cava, text):
    doc = nlp_cava(text)
    assert doc.text.replace(" ", "") == text.replace(" ", "")


