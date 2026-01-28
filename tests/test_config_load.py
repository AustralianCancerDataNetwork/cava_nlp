import json
import yaml
import pytest
from cava_nlp.namespaces.core.loader import _interpolate_json
from cava_nlp.namespaces.core.loader import _merge_components
from cava_nlp.namespaces.core.loader import load_pattern_file


def test_interpolate_json_simple(monkeypatch):
    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.resolver.resolve",
        lambda name: 123 if name == "value" else None,
    )

    text = '{"a": ${value}}'
    expanded = _interpolate_json(text)

    assert json.loads(expanded) == {"a": 123}


def test_interpolate_json_string(monkeypatch):
    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.resolver.resolve",
        lambda name: "abc",
    )

    text = '{"a": ${foo}}'
    expanded = _interpolate_json(text)

    assert json.loads(expanded) == {"a": "abc"}


def test_interpolate_json_list(monkeypatch):
    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.resolver.resolve",
        lambda name: [1, 2, 3],
    )

    text = '{"a": ${foo}}'
    expanded = _interpolate_json(text)

    assert json.loads(expanded) == {"a": [1, 2, 3]}


from cava_nlp.namespaces.core.loader import _interpolate_yaml

def test_interpolate_yaml_scalar(monkeypatch):
    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.resolver.resolve",
        lambda name: 42,
    )

    text = "value: ${foo}"
    expanded = _interpolate_yaml(text)

    assert yaml.safe_load(expanded) == {"value": 42}


def test_interpolate_yaml_mapping(monkeypatch):
    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.resolver.resolve",
        lambda name: {"a": 1, "b": 2},
    )

    text = "data: ${foo}"
    expanded = _interpolate_yaml(text)

    assert yaml.safe_load(expanded) == {"data": {"a": 1, "b": 2}}


def test_merge_components_simple():
    base = {
        "components": {
            "a": {"x": 1},
        }
    }
    other = {
        "components": {
            "b": {"y": 2},
        }
    }

    merged = _merge_components(base, other)

    assert merged["components"] == {
        "a": {"x": 1},
        "b": {"y": 2},
    }

    # Ensure immutability
    assert base["components"] == {"a": {"x": 1}}


def test_merge_components_override():
    base = {
        "components": {
            "a": {"x": 1},
        }
    }
    other = {
        "components": {
            "a": {"x": 99},
        }
    }

    merged = _merge_components(base, other)

    assert merged["components"]["a"]["x"] == 99



def test_load_pattern_file_success(monkeypatch, tmp_path):
    rulesets = tmp_path / "rulesets"
    rulesets.mkdir()

    file = rulesets / "test.json"
    file.write_text(json.dumps({"token": []}))

    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.PATTERN_ROOT",
        rulesets,
    )
    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.validate_pattern_schema",
        lambda data, filename: None,
    )

    data = load_pattern_file("test.json")
    assert data == {"token": []}


def test_load_pattern_file_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.PATTERN_ROOT",
        tmp_path,
    )

    with pytest.raises(FileNotFoundError):
        load_pattern_file("missing.json")


def test_load_pattern_file_invalid_json(monkeypatch, tmp_path):
    rulesets = tmp_path / "rulesets"
    rulesets.mkdir()

    file = rulesets / "bad.json"
    file.write_text("{ invalid json }")

    monkeypatch.setattr(
        "cava_nlp.namespaces.core.loader.PATTERN_ROOT",
        rulesets,
    )

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_pattern_file("bad.json")



from cava_nlp.namespaces.core.loader import load_engine_config

def test_load_engine_config_simple(tmp_path):
    cfg = tmp_path / "base.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "components": {
                    "a": {"factory": "rule_engine"},
                }
            }
        )
    )

    data = load_engine_config(cfg)
    assert "components" in data
    assert "a" in data["components"]


def test_load_engine_config_with_include(tmp_path):
    base = tmp_path / "base.yaml"
    inc = tmp_path / "inc.yaml"

    inc.write_text(
        yaml.safe_dump(
            {
                "components": {
                    "b": {"factory": "rule_engine"},
                }
            }
        )
    )

    base.write_text(
        yaml.safe_dump(
            {
                "include": ["inc.yaml"],
                "components": {
                    "a": {"factory": "rule_engine"},
                }
            }
        )
    )

    data = load_engine_config(base)

    assert set(data["components"].keys()) == {"a", "b"}


def test_load_engine_config_bad_root(tmp_path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("- not a mapping")

    with pytest.raises(ValueError, match="Engine config must be a mapping"):
        load_engine_config(cfg)


def test_load_engine_config_bad_include_type(tmp_path):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "include": "not-a-list",
            }
        )
    )

    with pytest.raises(ValueError, match="'include' must be a list"):
        load_engine_config(cfg)