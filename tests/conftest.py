import pytest
from pathlib import Path
from cava_nlp import CaVaLang

@pytest.fixture
def temp_rules_dir(tmp_path: Path) -> Path:
    rules = tmp_path / "rulesets"
    rules.mkdir()
    return rules

@pytest.fixture
def nlp_cava():
    nlp = CaVaLang()

    # Optional: drop sectionizers to avoid needing full context rule files
    for name, _ in list(nlp.pipeline):
        if "sectionizer" in name or "context" in name:
            nlp.remove_pipe(name)

    return nlp

@pytest.fixture
def raw_text():
    return """
    Patient email john.doe@example.com had ECOG 1.
    Weight 70kg and WBC 1e3.
    Follow-up on 01/02/2024.
    """

@pytest.fixture
def processed_doc(nlp_cava, raw_text):
    return nlp_cava(raw_text)
