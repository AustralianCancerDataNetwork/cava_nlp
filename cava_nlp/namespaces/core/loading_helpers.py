from typing_extensions import TypeGuard
from typing import Any, Mapping, Optional

def _is_str_keyed_mapping(obj: Any) -> TypeGuard[Mapping[str, Any]]:
    if not isinstance(obj, Mapping):
        return False
    return all(isinstance(k, str) for k in obj) # type: ignore

def ensure_str_keyed_mapping(obj: Any, *, context: Optional[str]=None) -> Mapping[str, Any]:
    if not _is_str_keyed_mapping(obj):
        raise ValueError(f"{context} must be a mapping with string keys")
    return obj
