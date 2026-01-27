from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

@dataclass(frozen=True)
class ContextConfig:
    span_attrs: Mapping[str, Mapping[str, Any]]
    rules_path: Path

DEFAULT_CONTEXT_CONFIG = ContextConfig(
    span_attrs={
        "CURRENT": {"is_current": True},
        "DATEOF": {"date_of": True},
    },
    rules_path=Path(__file__).parent / "_context_config.json",
)
