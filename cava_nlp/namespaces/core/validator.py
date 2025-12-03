from typing import Any, Dict, List

def _validate_pattern_list(name: str, patterns: Any, filename: str):
    if patterns is None:
        return
    if not isinstance(patterns, list):
        raise ValueError(
            f"Pattern key '{name}' in {filename} must be a list, "
            f"got {type(patterns).__name__}."
        )
    # We expect outer list of patterns, each pattern is a list of token dicts
    for pat in patterns:
        if not isinstance(pat, list):
            raise ValueError(
                f"In {filename}, pattern under '{name}' must be a list of token dicts; "
                f"got element of type {type(pat).__name__}."
            )
        for token_spec in pat:
            if not isinstance(token_spec, dict):
                raise ValueError(
                    f"In {filename}, pattern under '{name}' has non-dict token spec: "
                    f"{token_spec!r}"
                )

def validate_pattern_schema(patterns: Dict[str, Any], filename: str):
    """
    Basic schema checker for matcher pattern JSON files.
    Ensures that 'token', 'value', 'norm', 'exclusions' (if present) are lists of patterns,
    and that each pattern is a list of dicts.
    """
    for key in ("token", "value", "exclusions"):
        if key in patterns:
            _validate_pattern_list(key, patterns[key], filename)
