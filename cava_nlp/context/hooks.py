from spacy.language import Language
import json
from typing import Any, Dict, Mapping
from pathlib import Path
from .config import ContextConfig, DEFAULT_CONTEXT_CONFIG, CONTEXT_PROFILES
from .registry import register_context_extensions, LOCAL_ATTRIBUTES

MEDSPACY_CONTEXT_FACTORY = "medspacy_context"

def _validate_context_rules(path: Path) -> None:
    try:
        data = json.loads(path.read_text())
    except Exception as e:
        raise ValueError(f"Context rules file is not valid JSON: {path}") from e

    if "context_rules" not in data:
        raise ValueError(
            f"Context rules file must contain a top-level 'context_rules' key: {path}"
        )

def _merge_span_attrs(
    extra: Mapping[str, Mapping[str, Any]] | None,
) -> Dict[str, Dict[str, Any]]:
    """
    Merge medSpaCy DEFAULT_ATTRIBUTES with CaVa / user-defined additions.

    - medSpaCy defaults are preserved
    - extra entries override defaults if keys collide
    - returns a fresh dict (no mutation of inputs)
    """

    merged: Dict[str, Dict[str, Any]] = {
        key: dict(value) for key, value in LOCAL_ATTRIBUTES.items()
    }

    if extra:
        for key, value in extra.items():
            merged[key] = dict(value)

    return merged

def enable_context(
    nlp: Language,
    *,
    config: ContextConfig | None = None,
    name: str = MEDSPACY_CONTEXT_FACTORY,
    before: str | None = None,
    after: str | None = None,
    profile: str | None = None,
) -> None:
    
    if config and profile:
        raise ValueError("Specify either 'config' or 'profile', not both")
    
    if profile:
        if profile not in CONTEXT_PROFILES:
            raise ValueError(f"Unknown context profile: {profile}")
        profile_path = CONTEXT_PROFILES[profile]
        config = ContextConfig(
            # todo: combine with user override? we can get
            # category from the json but how do we get the 
            # attribute label?
            span_attrs=DEFAULT_CONTEXT_CONFIG.span_attrs,
            rules_path=profile_path
        )
    
    if config is None:
        config = DEFAULT_CONTEXT_CONFIG

    merged_span_attrs = _merge_span_attrs(config.span_attrs)
    register_context_extensions(span_attrs=merged_span_attrs)
    
    _validate_context_rules(config.rules_path)

    if name in nlp.pipe_names:
        raise ValueError(f"Pipeline already contains a component named '{name}'")

    nlp.add_pipe(
        MEDSPACY_CONTEXT_FACTORY,
        name=name,
        config={
            "span_attrs": merged_span_attrs,
            "rules": str(config.rules_path),
        },
        before=before,
        after=after,
    )


