
from __future__ import annotations
import importlib
from typing import Any, Optional

# The Resolver class holds namespace handlers
from .loader import load_pattern_file

# Load regex primitives
from cava_nlp.namespaces import regex as regex_pkg


def resolve_regex(name: Optional[str]) -> Any:
    """
    Resolve atomic regex primitives.

    Examples:
        ${regex.year_regex}
        ${regex.numeric_month_regex}
        ${regex.emails}

    All resolved from:
        cava_nlp.namespaces.regex
    """

    if not name:
        raise ValueError("regex namespace requires an attribute name")

    if hasattr(regex_pkg, name):
        return getattr(regex_pkg, name)

    raise KeyError(f"Unknown regex variable: regex.{name!r}")


def resolve_ruleset(path: str) -> Any:
    """
    Resolve JSON rule patterns from ruleset files.

    Examples:
        ${rulesets.weight.token}
        ${rulesets.ecog.value}
        ${rulesets.ecog.exclusions}

    This loads:
        cava_nlp/namespaces/rulesets/<name>.json
    and extracts the key.
    """

    if not path:
        raise ValueError("rulesets namespace requires file.key")

    try:
        file, key = path.split(".", 1)
    except ValueError:
        raise ValueError(
            f"rulesets namespace must be file.key, got: {path!r}"
        ) from None

    data = load_pattern_file(f"{file}.json")

    if key not in data:
        raise KeyError(f"ruleset '{file}' has no key '{key}'")

    return data[key]


def resolve_construct(path: str) -> Any:
    """
    Resolve constructs from Python modules.

    Examples:
        ${constructs.value_extractor.numeric_range}
        ${constructs.ecog.preface_patterns}

    Loads modules dynamically:
        cava_nlp.namespaces.constructs.<module>

    Then retrieves attributes inside.
    """

    if not path:
        raise ValueError("constructs namespace requires module.attr")

    try:
        module_name, attr = path.split(".", 1)
    except ValueError:
        raise ValueError(
            f"constructs namespace must be module.attr, got: {path!r}"
        ) from None

    module_path = f"cava_nlp.namespaces.constructs.{module_name}"

    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise KeyError(f"Unknown constructs module: {module_name!r}") from None

    if not hasattr(module, attr):
        raise KeyError(
            f"constructs.{module_name} has no attribute {attr!r}"
        )

    return getattr(module, attr)