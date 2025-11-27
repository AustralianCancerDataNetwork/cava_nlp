class VariableResolver:
    """Standalone resolver with pluggable namespaces."""

    def __init__(self):
        self.namespaces = {}

    def register(self, namespace: str, func):
        """Register a function that resolves names in a namespace."""
        self.namespaces[namespace] = func

    def resolve(self, name: str):
        """
        Resolve names like:
            weight_units
            patterns.weight.token
            regex.email
        """
        # patterns.weight.token → namespace=patterns, remainder=weight.token
        if "." in name:
            namespace, rest = name.split(".", 1)
        else:
            namespace, rest = name, None

        if namespace not in self.namespaces:
            raise KeyError(f"Unknown namespace: {namespace}")

        return self.namespaces[namespace](rest)

resolver = VariableResolver()