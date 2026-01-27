from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


PROFILE_DIR = Path(__file__).parent / "profiles"

CONTEXT_PROFILES = {
    "clinical": PROFILE_DIR / "clinical.json",
    "lab": PROFILE_DIR / "lab.json",
    "tests": PROFILE_DIR / "tests.json",
}


@dataclass(frozen=True)
class ContextConfig:
    span_attrs: Mapping[str, Mapping[str, Any]]
    rules_path: Path

DEFAULT_CONTEXT_CONFIG = ContextConfig(
    span_attrs={
        "CURRENT": {"is_current": True},
        "DATEOF": {"date_of": True},
        "UNCONFIRMED": {"is_unconfirmed": True},
        "POSITIVE": {"is_positive": True},
    },
    rules_path=PROFILE_DIR / "clinical.json",
)
