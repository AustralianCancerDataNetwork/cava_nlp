import pytest
from typing import Any, Dict

from cava_nlp.namespaces.core.rule_config import (
    RuleEngineConfig,
    RulePatternConfig,
)

def test_rule_engine_config_minimal() -> None:
    raw: Dict[str, Any] = {
        "span_label": "ecog",
        "patterns": {
            "ecog": {
                "token_patterns": [[{"TEXT": "ECOG"}]],
                "value": 1,
            }
        },
    }

    cfg = RuleEngineConfig.from_mapping(raw)

    assert cfg.span_label == "ecog"
    assert cfg.entity_label == ""
    assert cfg.value_type == "str"
    assert cfg.value_aggregation == "first"
    assert cfg.merge_ents is False

    assert "ecog" in cfg.patterns
    p = cfg.patterns["ecog"]

    assert isinstance(p, RulePatternConfig)
    assert p.value == 1
    assert p.value_patterns is None


def test_rule_engine_config_full() -> None:
    raw: Dict[str, Any] = {
        "span_label": "variant",
        "entity_label": "GENOMIC",
        "value_type": "str",
        "value_aggregation": "join",
        "merge_ents": True,
        "patterns": {
            "egfr": {
                "token_patterns": [[{"LOWER": "egfr"}]],
                "value": "egfr",
            },
            "alk": {
                "token_patterns": [[{"LOWER": "alk"}]],
                "value_patterns": [[{"IS_DIGIT": True}]],
                "exclusions": [[{"LOWER": "fusion"}]],
            },
        },
    }

    cfg = RuleEngineConfig.from_mapping(raw)

    assert cfg.span_label == "variant"
    assert cfg.entity_label == "GENOMIC"
    assert cfg.value_type == "str"
    assert cfg.value_aggregation == "join"
    assert cfg.merge_ents is True

    assert set(cfg.patterns) == {"egfr", "alk"}

    alk = cfg.patterns["alk"]
    assert alk.value is None
    assert alk.value_patterns is not None
    assert alk.exclusions is not None


def test_missing_span_label_raises() -> None:
    raw = {
        "patterns": {
            "x": {
                "token_patterns": [[{"TEXT": "X"}]],
                "value": "x",
            }
        }
    }

    with pytest.raises(ValueError, match="span_label"):
        RuleEngineConfig.from_mapping(raw)


def test_patterns_must_be_mapping() -> None:
    raw = {
        "span_label": "ecog",
        "patterns": [],
    }

    with pytest.raises(ValueError, match="patterns"):
        RuleEngineConfig.from_mapping(raw)


def test_pattern_missing_token_patterns() -> None:
    raw = {
        "span_label": "ecog",
        "patterns": {
            "bad": {
                "value": 1
            }
        },
    }

    with pytest.raises(ValueError, match="missing 'token_patterns'"):
        RuleEngineConfig.from_mapping(raw)


def test_pattern_missing_value_and_value_patterns() -> None:
    raw = {
        "span_label": "ecog",
        "patterns": {
            "bad": {
                "token_patterns": [[{"TEXT": "ECOG"}]],
            }
        },
    }

    with pytest.raises(ValueError, match="must define either"):
        RuleEngineConfig.from_mapping(raw)


def test_pattern_key_must_be_string() -> None:
    raw = {
        "span_label": "ecog",
        "patterns": {
            123: {  # type: ignore[dict-item]
                "token_patterns": [[{"TEXT": "ECOG"}]],
                "value": 1,
            }
        },
    }

    with pytest.raises(ValueError):
        RuleEngineConfig.from_mapping(raw)


def test_config_round_trip_properties() -> None:
    raw = {
        "span_label": "test",
        "patterns": {
            "a": {
                "token_patterns": [[{"LOWER": "a"}]],
                "value": "a",
            }
        },
    }

    cfg = RuleEngineConfig.from_mapping(raw)

    # Contract-style assertions
    assert cfg.patterns["a"].token_patterns
    assert isinstance(cfg.patterns["a"].token_patterns, list)
