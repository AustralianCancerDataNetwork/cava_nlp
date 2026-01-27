from spacy.language import Language
import json
from pathlib import Path
from .config import ContextConfig, DEFAULT_CONTEXT_CONFIG
from .registry import register_context_extensions

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


def enable_context(
    nlp: Language,
    *,
    config: ContextConfig = DEFAULT_CONTEXT_CONFIG,
    name: str = MEDSPACY_CONTEXT_FACTORY,
    before: str | None = None,
    after: str | None = None,
) -> None:
    register_context_extensions(span_attrs=config.span_attrs)
    
    _validate_context_rules(config.rules_path)

    if name in nlp.pipe_names:
        raise ValueError(f"Pipeline already contains a component named '{name}'")

    nlp.add_pipe(
        MEDSPACY_CONTEXT_FACTORY,
        name=name,
        config={
            "span_attrs": config.span_attrs,
            "rules": str(config.rules_path),
        },
        before=before,
        after=after,
    )


