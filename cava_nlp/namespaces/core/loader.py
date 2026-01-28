import json, re, yaml
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, cast, Match, Dict

from cava_nlp.namespaces.core.validator import validate_pattern_schema
from cava_nlp.namespaces.core.namespace import resolver
from .loading_helpers import ensure_str_keyed_mapping

VAR_RE = re.compile(r"\$\{([^}]+)\}")
PATTERN_ROOT = Path(__file__).parent.parent / "rulesets"

def _interpolate_json(text: str) -> str:
    """
    Interpolate ${...} variables inside a JSON string.

    Each ${var} expression is resolved via the namespace resolver and
    substituted with a JSON-encoded representation. Using ``json.dumps``
    ensures that the result is always valid JSON (strings are quoted,
    lists and objects are serialized correctly, etc.).

    Parameters
    ----------
    text : str
        Raw JSON text containing ${...} placeholders.

    Returns
    -------
    str
        JSON text with all placeholders expanded.
    """

    def repl(match: Match[str]) -> str:
        name = match.group(1)
        value = resolver.resolve(name)
        return json.dumps(value)

    return VAR_RE.sub(repl, text)


@lru_cache(maxsize=None)
def load_pattern_file(filename: str):
    """
    Load a ruleset JSON file with variable interpolation.

    Supports JSON references such as:
        ${regex.year_regex}
        ${constructs.ecog.preface_patterns}
        ${rulesets.weight.token}
    """
    path = PATTERN_ROOT / filename

    if not path.exists():
        raise FileNotFoundError(f"Pattern file not found: {path}")

    raw = path.read_text()
    expanded = _interpolate_json(raw)

    try:
        data = json.loads(expanded)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON after interpolation in {filename}: {e}"
        ) from e
    
    try:
        validate_pattern_schema(data, filename)
    except Exception as e:
        raise ValueError(f"Pattern schema validation failed for {filename}: {e}") from e

    return data


def _merge_components(
    base: Mapping[str, Any],
    other: Mapping[str, Any],
) -> Dict[str, Any]:


    """
    Merge `components` mappings from two engine configs.

    - Does NOT mutate inputs
    - Values from `other` override `base`
    - Returns a new dict
    """
    merged: Dict[str, Any] = dict(base)
    base_comps = ensure_str_keyed_mapping(base.get("components", {}))
    other_comps = ensure_str_keyed_mapping(other.get("components", {}))

    merged_components: Dict[str, Any] = dict(base_comps)
    merged_components.update(other_comps)

    merged["components"] = merged_components
    return merged



def _interpolate_yaml(text: str) -> str:
    """
    Interpolate ${...} variables inside a YAML string.

    Each ${var} expression is resolved via the namespace resolver and
    substituted with a YAML-safe inline representation.

    Parameters
    ----------
    text : str
        Raw YAML text containing ${...} placeholders.

    Returns
    -------
    str
        YAML text with all placeholders expanded.
    """

    def repl(match: Match[str]) -> str:
        value = resolver.resolve(match.group(1))
        # Dump as inline YAML (e.g. lists, dicts, scalars) and strip trailing newline
        return yaml.safe_dump(value, default_flow_style=True).strip()

    return VAR_RE.sub(repl, text)



@lru_cache(maxsize=None)
def load_engine_config(path: str | Path) -> Mapping[str, Any]:
    """
    Load engine config YAML with interpolation and support for 'include' lists.

    Example:
      include:
        - rules/basic.yaml
        - rules/oncology.yaml

      components:
        weight_value:
          factory: rule_engine
          config: ...
    """
    path = Path(path).resolve()
    raw = path.read_text()
    expanded = _interpolate_yaml(raw)
    raw: Any = yaml.safe_load(expanded) or {}

    if not isinstance(raw, Mapping):
        raise ValueError(
            f"Engine config must be a mapping, got {type(raw).__name__}"
        )

    config: Mapping[str, Any] = ensure_str_keyed_mapping(raw)

    raw_includes: Any = config.get("include", []) or []

    if not isinstance(raw_includes, list):
        raise ValueError(
            f"'include' must be a list, got {type(raw_includes).__name__}"
        )
    includes: list[str] = cast(list[str], raw_includes)

    base_dir = path.parent

    for inc in includes:
        inc_path = (base_dir / inc).resolve()
        inc_raw = inc_path.read_text()
        inc_expanded = _interpolate_yaml(inc_raw)
        inc_cfg: Any = ensure_str_keyed_mapping(yaml.safe_load(inc_expanded))

        # inc_cfg = yaml.safe_load(inc_expanded) or {}
        config = _merge_components(config, inc_cfg)

    return config