import pytest
from pathlib import Path

@pytest.fixture
def temp_rules_dir(tmp_path: Path) -> Path:
    rules = tmp_path / "rulesets"
    rules.mkdir()
    return rules
