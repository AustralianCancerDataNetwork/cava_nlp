import pytest
from pathlib import Path

import spacy
from spacy.tokens import Span

from cava_nlp.context.config import ContextConfig, DEFAULT_CONTEXT_CONFIG
from cava_nlp.context.registry import register_context_extensions
from cava_nlp.context.hooks import enable_context

def test_context_config_is_declarative():
    import importlib
    import cava_nlp.context.config as config

    importlib.reload(config)
    cfg = config.DEFAULT_CONTEXT_CONFIG

    assert isinstance(cfg, config.ContextConfig)
    assert isinstance(cfg.rules_path, Path)
    assert cfg.rules_path.name.endswith(".json")


def test_register_context_extensions_idempotent():
    # First registration
    register_context_extensions()

    assert Span.has_extension("is_current")
    assert Span.has_extension("date_of")

    # Second call should be a no-op (not error)
    register_context_extensions()

    assert Span.has_extension("is_current")
    assert Span.has_extension("date_of")


def test_context_not_enabled_by_default():
    nlp = spacy.blank("en")

    assert "medspacy_context" not in nlp.pipe_names


def test_enable_context_adds_pipeline_component():
    nlp = spacy.blank("en")

    enable_context(nlp)

    assert "medspacy_context" in nlp.pipe_names


def test_enable_context_registers_extensions():
    nlp = spacy.blank("en")

    enable_context(nlp)

    assert Span.has_extension("is_current")
    assert Span.has_extension("date_of")


def test_enable_context_duplicate_name_raises():
    nlp = spacy.blank("en")

    enable_context(nlp)

    with pytest.raises(ValueError, match="already contains a component"):
        enable_context(nlp)


def test_enable_context_custom_config(tmp_path):
    rules = tmp_path / "rules.json"
    rules.write_text('{"context_rules": []}')
    
    cfg = ContextConfig(
        span_attrs={"CUSTOM": {"foo": True}},
        rules_path=rules,
    )

    nlp = spacy.blank("en")
    enable_context(nlp, config=cfg, name="custom_context")

    assert "custom_context" in nlp.pipe_names


def test_enable_context_pipe_placement():
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    enable_context(nlp, after="sentencizer")

    assert nlp.pipe_names.index("medspacy_context") == (
        nlp.pipe_names.index("sentencizer") + 1
    )
