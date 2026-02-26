from spacy.language import Language
from spaczz.matcher.regexmatcher import RegexMatcher, REGEX_SPAN_KEY
from cava_nlp.namespaces.core.loader import load_engine_config
from pathlib import Path
from typing import Optional

@Language.factory(
    "regex_matcher",
    default_config={
        "pattern_config": None,
        "component_name": None,
    },
)
def create_regex_matcher(
    nlp, 
    name,
    pattern_config: Optional[dict[str, list[str]]] = None,
    component_name: Optional[str] = None
):
    if pattern_config is None:
        raise NotImplementedError("Currently only supports pattern_config input. Component-based config loading is not implemented yet.")

    assert isinstance(pattern_config, dict), "pattern_config must be a dictionary of label to list of regex patterns"

    matcher = RegexMatcher(nlp.vocab)
    for label, patterns in pattern_config.items():
        matcher.add(label, patterns)

    return matcher