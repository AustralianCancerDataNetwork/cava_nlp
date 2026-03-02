from spacy.language import Language
from spaczz.matcher.regexmatcher import RegexMatcher, REGEX_SPAN_KEY
from cava_nlp.namespaces.core.loader import load_engine_config
from pathlib import Path
from typing import Optional

from ..namespaces.regex.cancer import (
    cm_rStage,
    cm_rSite,
)

import logging
logger = logging.getLogger(__name__)

CONFIG = {
    "Stage": cm_rStage,
    "Site": cm_rSite,
}

@Language.factory(
    "regex_matcher",
    default_config={
        "pattern_config": None,
        "component_names": None,
    },
)
def create_regex_matcher(
    nlp, 
    name,
    pattern_config: Optional[dict[str, list[str]]] = None,
    component_names: Optional[list[str] | str] = None
):
    if pattern_config is None:
        pattern_config = {}
        assert component_names is not None, "Either pattern_config or component_name must be provided"
        if isinstance(component_names, str):
            component_names = [component_names]

        for comp in component_names:
            try:
                pattern_config[comp] = CONFIG[comp]
            except KeyError:
                logger.warning(f"Component name '{comp}' not found in CONFIG. Skipping.")
                continue

        if not pattern_config:
            raise ValueError("No valid component names provided. Cannot create regex matcher.")

    assert isinstance(pattern_config, dict), "pattern_config must be a dictionary of label to list of regex patterns"
    matcher = RegexMatcher(nlp.vocab)
    for label, patterns in pattern_config.items():
        matcher.add(label, patterns)

    return matcher