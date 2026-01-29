from pathlib import Path
from typing import Optional

from spacy.language import Language

from .rule_engine import RuleEngine, RuleEngineConfig
from cava_nlp.namespaces.core.loader import load_engine_config

ENGINE_CONFIG_ROOT = Path(__file__).parent / "engine_config"

@Language.factory(
    "rule_engine",
    default_config={
        "engine_config_path": None,
        "component_name": None,
    },
)
def create_rule_engine(
    nlp: Language,
    name: str,
    engine_config_path: Optional[Path],
    component_name: Optional[str],
) -> RuleEngine:
    if engine_config_path is None:
        engine_config_path = ENGINE_CONFIG_ROOT / "default.yaml"
    if component_name is None:
        raise ValueError("component_name is required for rule_engine")

    full_cfg = load_engine_config(engine_config_path)
    comp_cfg = full_cfg["components"].get(component_name)

    if comp_cfg is None:
        raise ValueError(f"Component '{component_name}' not found in engine config.")
    engine_cfg = RuleEngineConfig.from_mapping(comp_cfg["config"])
    return RuleEngine(nlp=nlp, name=name, config=engine_cfg)
