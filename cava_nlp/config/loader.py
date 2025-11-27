import json, re, yaml
from functools import lru_cache
from pathlib import Path
from cava_nlp import regex as rx
from cava_nlp.rule_engine.validator import validate_pattern_schema
from cava_nlp.config.namespace import resolver

VAR_RE = re.compile(r"\$\{([^}]+)\}")
PATTERN_ROOT = Path(__file__).parent / "patterns"


def _resolve_variable(name: str):
    """
    Resolve names like:
        - weight_units                 (regex module)
        - patterns.weight.token        (pattern file)
    """
    if hasattr(rx, name):
        return getattr(rx, name)

    if name.startswith("patterns."):
        parts = name.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid patterns reference: {name}")

        _, file, key = parts
        pattern_dict = load_pattern_file(f"{file}.json")

        if key not in pattern_dict:
            raise KeyError(f"{key!r} not found in pattern file {file}.json")

        return pattern_dict[key]

    raise KeyError(f"Unknown placeholder: {name}")


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
    path = PATTERN_ROOT / filename
    with open(path, "r") as f:
        raw = f.read()
    expanded = _interpolate_json(raw)
    data = json.loads(expanded)
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

def patterns_namespace(name):
    file, key = name.split(".", 1)
    data = load_pattern_file(f"{file}.json")
    if key not in data:
        raise KeyError(f"{key} not found in {file}.json")
    return data[key]


resolver.register("regex", lambda name: getattr(rx, name))
resolver.register("patterns", patterns_namespace)
resolver.register("default", lambda name: getattr(rx, name))