from __future__ import annotations

from typing import Any, Callable, Dict, Optional

NamespaceResolver = Callable[[Optional[str]], Any]

class VariableResolver:
    
    """
    Standalone variable resolver with pluggable namespaces.

    Names are resolved using dot-notation:

        regex.year_regex
        rulesets.ecog.token
        constructs.ecog.preface_patterns

    Each namespace is backed by a callable that accepts the remainder
    of the path (or None) and returns a resolved value.
    """

    def __init__(self) -> None:
        self.namespaces: Dict[str, NamespaceResolver] = {}

    def register(self, namespace: str, func: NamespaceResolver) -> None:
        """
        Register a namespace resolver.

        Parameters
        ----------
        namespace : str
            The namespace prefix (e.g. "regex", "rulesets").
        func : Callable[[Optional[str]], Any]
            Resolver function called with the remainder of the path.
        """
        self.namespaces[namespace] = func
    
    def resolve(self, name: str) -> Any:
        """
        Resolve a variable reference.

        Examples
        --------
        - "regex.year_regex"
        - "rulesets.ecog.token"
        - "weight_units"

        Returns
        -------
        Any
            The resolved object.
        """
        if "." in name:
            namespace, rest = name.split(".", 1)
        else:
            namespace, rest = name, None

        try:
            resolver = self.namespaces[namespace]
        except KeyError:
            raise KeyError(f"Unknown namespace: {namespace}") from None

        return resolver(rest)
    
resolver = VariableResolver()