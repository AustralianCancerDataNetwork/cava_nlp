from functools import partial
from typing import Any, Callable, Optional, TypeVar, Iterable, Sequence, Generic, List
from spacy.tokens import Span

"""
Type of raw values produced by matchers.

In practice this is most often `str`, but may also be richer objects
(e.g. range objects, dataclasses, or lightweight wrappers) depending
on the extraction pipeline.
"""
Raw = TypeVar("Raw")

"""
Type of the final, resolved value returned to the caller.

Examples include `int`, `float`, `str`, or domain-specific types.
"""
Final = TypeVar("Final")


"""
Callable which converts a raw value into a final typed value.

Casters must be *total* and *safe*: they should return ``None`` instead
of raising when conversion fails.
"""
Caster = Callable[[Raw], List[Final]]

"""
Callable which reduces a sequence of raw values into a single raw value.

Aggregators do not perform final casting; they only select or combine
raw inputs.
"""
Aggregator = Callable[[List[Final]], Optional[Final]]

"""
Loosely-typed aggregator signature used for registry dictionaries.
"""
AggregatorAny = Callable[[Sequence[Any]], Optional[Any]]

def safe_cast(func: Callable[[Any], Raw], value: Span | None) -> List[Raw]:
    """
    Safely apply a casting function to a Span.

    This helper wraps a potentially unsafe cast (e.g. ``int()``, ``float()``)
    and converts common failures into ``None``.

    Parameters
    ----------
    func
        A callable performing a conversion (e.g. ``int``, ``float``, ``str``).
    value
        The span to convert.

    Returns
    -------
    Optional[Raw]
        The converted value on success, or ``None`` if conversion fails
        or if the input value is ``None``.

    Notes
    -----
    This function intentionally swallows ``ValueError`` and ``TypeError``.
    It is designed for use in rule pipelines where failed conversions
    are expected and non-fatal.
    """
    if value is None or len(value) == 0:
        return []
    # if there is a custom ._.value attribute, use that
    if hasattr(value[0]._, 'value') and value[0]._.value is not None:
        extracted_val = value[0]._.value
        if not isinstance(extracted_val, List):
            if extracted_val is None:
                extracted_val = [value]
            else:
                extracted_val = [extracted_val] 
    else:
        extracted_val = [token.text for token in value]
    results: List[Raw] = [] 
    for vv in extracted_val: # type: ignore
        try:
            results.append(func(vv))
        except (ValueError, TypeError):
            continue
    return results

# Predefined caster registry for common types.
CASTERS: dict[str, Callable[[Any], List[Any]]] = {
    "int": partial(safe_cast, int),
    "float": partial(safe_cast, float),
    "str": partial(safe_cast, str),
}

def agg_max(
    raw_values: Iterable[Any]
) -> Optional[Any]:
    """
    Select the maximum numeric value from a collection of raw values.
    """
    return max(raw_values) if raw_values else None

def agg_min(
    raw_values: Iterable[Any]
) -> Optional[Any]:
    
    """
    Select the minimum numeric value from a collection of raw values.
    """
    return min(raw_values) if raw_values else None

def agg_join(raw_values: Iterable[Any]) -> str:

    """
    Join raw values into a single string.
    """
    if not raw_values:
        return ''
    return "".join(raw_values)

def agg_first(raw_values: Sequence[Any]) -> Optional[Any]:

    """
    Select the first raw value.
    """
    if not raw_values:
        return None
    return raw_values[0]

AGGREGATORS: dict[str, AggregatorAny] = {
    "max":   agg_max,
    "min":   agg_min,
    "join":  agg_join,
    "first": agg_first,
}

class ValueResolver(Generic[Raw, Final]):

    """
    Value resolution utilities for rule-based extraction.

    This module provides a small, composable framework for turning raw extracted
    values (usually strings or lightweight objects produced by matchers) into
    *final, typed values* suitable for downstream use.

    2-stage resolution process:

    1. **Aggregation**:
    Combine zero or more raw values extracted from a span into a single
    representative raw value (e.g. max, min, first, join).

    2. **Casting**:
    Convert the aggregated raw value into a final, typed value
    (e.g. int, float, str), handling failures safely.

    This separation allows rules to express concepts like:
    - “take the maximum ECOG score mentioned”
    - “join multiple tokens into a single string”
    - “prefer literal values over extracted ones”

    without baking domain logic into the rule engine itself.


    A `ValueResolver` encapsulates the policy for turning a collection of
    raw values into a single, meaningful result.

    Resolution follows a strict priority order:

    1. **Literal override** – if a literal value is provided, it always wins.
    2. **Aggregated extraction** – raw values are aggregated, then cast.
    3. **Fallback** – used when no literal or extractable value is available.

    """


    def __init__(
        self,
        caster: Caster[Raw, Final],
        aggregator: Aggregator[Final],
    ) -> None:
        self.caster = caster          
        self.aggregator = aggregator  

    def resolve(
        self,
        raw_values: Sequence[Raw],
        *,
        literal: Optional[Final] = None,
        fallback: Optional[Final] = None,
    ) -> Optional[Final]:        
        """
        Decide final value:

        1) literal if provided
        2) aggregated raw values if any
        3) fallback if no extracted values
        """
        if literal is not None:
            return literal
        typed = [x for y in [self.caster(r) for r in raw_values] for x in y]
        raw = self.aggregator(typed)
        return raw or fallback
