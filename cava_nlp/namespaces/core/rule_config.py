from typing import Any, Mapping, Sequence, Optional, Dict
from dataclasses import dataclass
from .loading_helpers import ensure_str_keyed_mapping

@dataclass(frozen=True)
class RulePatternConfig:
    token_patterns: Sequence[Any]
    value: Optional[Any] = None
    value_patterns: Optional[Sequence[Any]] = None
    exclusions: Optional[Sequence[Any]] = None

    @classmethod
    def from_mapping(cls, name: str, raw: Mapping[str, Any]) -> "RulePatternConfig":
        if "token_patterns" not in raw:
            raise ValueError(f"Pattern '{name}' missing 'token_patterns'")

        if raw.get("value") is None and raw.get("value_patterns") is None:
            raise ValueError(
                f"Pattern '{name}' must define either 'value' or 'value_patterns'"
            )

        return cls(
            token_patterns=raw["token_patterns"],
            value=raw.get("value"),
            value_patterns=raw.get("value_patterns"),
            exclusions=raw.get("exclusions"),
        )

@dataclass(frozen=True)
class RuleEngineConfig:
    span_label: str
    entity_label: str
    value_type: str
    value_aggregation: str
    merge_ents: bool
    patterns: Dict[str, RulePatternConfig]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "RuleEngineConfig":
        raw = ensure_str_keyed_mapping(raw, context="rule_engine.config")

        span_label = raw.get("span_label")
        if not isinstance(span_label, str):
            raise ValueError("span_label must be a string")

        entity_label = raw.get("entity_label", "")
        if not isinstance(entity_label, str):
            raise ValueError("entity_label must be a string")

        value_type = raw.get("value_type", "str")
        value_aggregation = raw.get("value_aggregation", "first")
        merge_ents = bool(raw.get("merge_ents", False))

        raw_patterns = ensure_str_keyed_mapping(
            raw.get("patterns"),
            context="rule_engine.config.patterns",
        )

        patterns: Dict[str, RulePatternConfig] = {}
        for name, p_raw in raw_patterns.items():
            patterns[name] = RulePatternConfig.from_mapping(
                name,
                ensure_str_keyed_mapping(
                    p_raw,
                    context=f"rule_engine.config.patterns.{name}",
                ),
            )
        return cls(
            span_label=span_label,
            entity_label=entity_label,
            value_type=value_type,
            value_aggregation=value_aggregation,
            merge_ents=merge_ents,
            patterns=patterns,
        )