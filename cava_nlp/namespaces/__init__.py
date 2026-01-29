from .core.namespace import resolver
from .core.registry import resolve_regex, resolve_ruleset, resolve_construct

resolver.register("regex", resolve_regex)
resolver.register("rulesets", resolve_ruleset)
resolver.register("constructs", resolve_construct)

__all__ = [
    "resolver",
]