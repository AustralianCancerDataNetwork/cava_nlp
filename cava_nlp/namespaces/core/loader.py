import json, re, yaml
from functools import lru_cache
from pathlib import Path
from cava_nlp.namespaces import regex as rx
from cava_nlp.namespaces.core.validator import validate_pattern_schema
from cava_nlp.namespaces.core.namespace import resolver

VAR_RE = re.compile(r"\$\{([^}]+)\}")
PATTERN_ROOT = Path(__file__).parent.parent / "rulesets"

def _interpolate_json(text: str):
    """
    Replace ${var} occurrences inside a JSON file/string.
    Ensures returned JSON is valid.
    """
    def repl(match):
        name = match.group(1)
        value = resolver.resolve(name)
        return json.dumps(value)  # Always valid JSON

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

    validate_pattern_schema(data, filename)
    return data

def _merge_components(base: dict, other: dict) -> dict:
    """Merge 'components' maps; later files override earlier ones with same names."""
    base_comps = base.get("components", {}) or {}
    other_comps = other.get("components", {}) or {}
    base_comps.update(other_comps)
    base["components"] = base_comps
    return base

def _interpolate_yaml(text):
    def repl(match):
        value = resolver.resolve(match.group(1))
        return yaml.safe_dump(value, default_flow_style=True).strip()
    return VAR_RE.sub(repl, text)

@lru_cache(maxsize=None)
def load_engine_config(path: str | Path):
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
    config = yaml.safe_load(expanded) or {}

    # Handle includes
    includes = config.get("include", []) or []
    base_dir = path.parent

    for inc in includes:
        inc_path = (base_dir / inc).resolve()
        inc_raw = inc_path.read_text()
        inc_expanded = _interpolate_yaml(inc_raw)
        inc_cfg = yaml.safe_load(inc_expanded) or {}
        config = _merge_components(config, inc_cfg)

    return config