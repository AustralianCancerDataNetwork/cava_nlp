
from spacy.matcher import Matcher
from spacy.tokens import Span, Token, SpanGroup
from spacy.util import filter_spans
from functools import partial

Span.set_extension("value", default=None, force=True)

# this could theoretically be extended to support user-defined 
# types or more complex casting but for now we just support 
# basic built-in types

def safe_cast(func, value):
    if value is None:
        return None
    try:
        return func(value)
    except (ValueError, TypeError):
        return None

CASTERS = {
  "int": partial(safe_cast, int),
  "float": partial(safe_cast, float),
  "str": partial(safe_cast, str),
}

def agg_max(raw_values, caster=CASTERS["float"]):
    # choose the max numeric value; ignore non-numeric
    nums = []
    for v in raw_values:
        try:
            nums.append(caster(v))
        except ValueError:
            pass
    if not nums:
        return None
    return max(nums)

def agg_min(raw_values, caster=CASTERS["float"]):
    nums = []
    for v in raw_values:
        try:
            nums.append(caster(v))
        except ValueError:
            pass
    if not nums:
        return None
    return min(nums)

def agg_join(raw_values):
    if not raw_values:
        return ''
    return " ".join(raw_values)

def agg_first(raw_values):
    if not raw_values:
        return None
    return raw_values[0]

AGGREGATORS = {
    "max":   agg_max,
    "min":   agg_min,
    "join":  agg_join,
    "first": agg_first,
}

class ValueResolver:
    def __init__(self, caster, aggregator):
        self.caster = caster          # callable: raw to typed
        self.aggregator = aggregator  # callable: list[typed] to typed/None

    def resolve(self, raw_values, literal=None, fallback=None):
        """
        Decide final value:

        1) literal if provided
        2) aggregated raw values if any
        3) fallback if no extracted values
        """
        if literal is not None:
            return literal

        raw = self.aggregator(raw_values)
        if raw is not None:
            return self.caster(raw)   # cast after aggregation

        return fallback


class RuleEngine:
    """
    Generic rule engine component.

    Config (per instance):

    - span_label: str                # span-group name e.g "weight"
    - entity_label: Optional[str]    # span label, e.g. "WEIGHT"
    - value_type: Optional[str]      # type to cast value to: "int", "float", "str" - defaults string
    - patterns: dict                 # spaCy Matcher patterns (outer list)
    - patterns.value: Optional[float|str]     # literal value to assign to matched span
    - patterns.value_patterns: Optional[list] # patterns to extract numeric portion within span
    - patterns.exclusions: Optional[list]     # patterns to suppress spans
    - merge_ents: Optional[bool]              # whether to merge matched span into a single token
    """

    def __init__(self, nlp, name, config):
        self.vocab = nlp.vocab
        self.name = name
        self.cfg = config

        self.span_label = config.get("span_label")
        self.entity_label = config.get("entity_label", "")

        value_type = config.get("value_type", "str").lower()
        agg_name = config.get("value_aggregation", "first").lower()

        self.resolver = ValueResolver(
            caster=CASTERS[value_type] if value_type in CASTERS else CASTERS["str"],
            aggregator=AGGREGATORS[agg_name] if agg_name in AGGREGATORS else AGGREGATORS["first"]
        )

        self.merge_ents = config.get("merge_ents", False)
        
        Span.set_extension(self.span_label, default=None, force=True)

        self.matchers = {}
        patterns_cfg = config.get("patterns", {})

        for var_name, cfg in patterns_cfg.items():    
            literal_value = cfg.get("value")  
            
            val_matcher = None
            exclusion_matcher = None

            if literal_value is None:
                val_patterns = cfg.get("value_patterns")
                if val_patterns is None:
                    raise ValueError(f"Either 'value' or 'value_patterns' must be specified for pattern '{var_name}'")
                val_matcher = Matcher(self.vocab)
                val_matcher.add(self.span_label + "_value", val_patterns)
            
            exclusion = cfg.get("exclusions")
            if exclusion is not None:
                exclusion_matcher = Matcher(self.vocab)
                exclusion_matcher.add(self.span_label + "_exclusion", exclusion)

            pats = cfg["token_patterns"]  
            
            m = Matcher(self.vocab)
            m.add(var_name, pats)

            self.matchers[var_name] = {
                "matcher": m,
                "literal_value": literal_value,
                "value_matcher": val_matcher,
                "exclusion": exclusion_matcher 
            }

    def _extract_raw_values(self, span, matcher):
        if not matcher:
            return []
        matches = matcher(span)
        raw = []
        for _, s, e in matches:
            raw.append(span[s:e])
        return [t.text for t in filter_spans(raw)]

    def find_spans(self, doc):
        spans = []
        for group_name, config in self.matchers.items():
            matcher = config.get("matcher")
            exclusion_matcher = config.get("exclusion")
            fallback = config.get("literal_value") or group_name
            matches = matcher(doc)
            var_spans = []
            for _, s, e in matches:
                sp = Span(doc, s, e, label=group_name)
                raw_values = self._extract_raw_values(doc[s:e], config.get("value_matcher"))
                sp._.value = self.resolver.resolve(
                    raw_values,
                    literal=config.get("literal_value"),
                    fallback=fallback
                )
                var_spans.append(sp)
            # apply exclusions
            if exclusion_matcher:
                excl = exclusion_matcher(doc)
                excl_spans = [Span(doc, s, e) for _, s, e in excl]
                var_spans = [sp for sp in var_spans if not any(
                    sp.start_char >= ex.start_char and sp.end_char <= ex.end_char
                    for ex in excl_spans
                )]
            spans.extend(var_spans)
        return filter_spans(spans)

    def __call__(self, doc):
        spans = self.find_spans(doc)
        with doc.retokenize() as retok:
            for sp in spans:
                if self.cfg.get("merge_ents", False):
                    retok.merge(sp)
                if self.span_label not in doc.spans:
                    doc.spans[self.span_label] = SpanGroup(doc)
                doc.spans[self.span_label].append(sp)
                if self.entity_label:
                    doc.ents += (Span(doc, sp.start, sp.end, label=self.entity_label),)
        return doc