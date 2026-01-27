from spacy.tokens import Span
from medspacy.context import DEFAULT_ATTRIBUTES  # type: ignore[import-untyped]
from typing import Mapping, Any

_baseline_registered = False

def register_context_extensions(
        *,
    span_attrs: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    """
    Register required spaCy Span extensions and medSpaCy attribute mappings.

    If span_attrs are provided, ensures all referenced Span extensions exist.
    """
    global _baseline_registered

    if not _baseline_registered:        
        Span.set_extension("is_current", default=False, force=True)
        Span.set_extension("date_of", default=False, force=True)

        DEFAULT_ATTRIBUTES.update({
            "CURRENT": {"is_current": True},
            "DATEOF": {"date_of": True},
        })
        _baseline_registered = True

    # Register custom extensions declared in config
    if span_attrs:
        for _, attr_dict in span_attrs.items():
            for attr_name in attr_dict.keys():
                if not Span.has_extension(attr_name):
                    Span.set_extension(attr_name, default=None)
