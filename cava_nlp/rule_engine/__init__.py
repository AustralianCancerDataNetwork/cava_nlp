from spacy.language import Language
from .rule_engine import RuleEngine  
from cava_nlp.namespaces.core.loader import load_engine_config
from pathlib import Path

ENGINE_CONFIG_ROOT = Path(__file__).parent / "engine_config"

@Language.factory(
    "rule_engine",
    default_config={
        "engine_config_path": None,
        "component_name": None,
    },
)
def create_rule_engine(nlp, name, engine_config_path, component_name):
    if engine_config_path is None:
        engine_config_path = ENGINE_CONFIG_ROOT / "default.yaml"
    if component_name is None:
        raise ValueError("component_name is required for rule_engine")

    full_cfg = load_engine_config(engine_config_path)
    comp_cfg = full_cfg["components"].get(component_name)

    if comp_cfg is None:
        raise ValueError(f"Component '{component_name}' not found in engine config.")

    return RuleEngine(nlp=nlp, name=name, config=comp_cfg["config"])
