
from spacy.matcher import Matcher
from spacy.tokens import Span, Token, SpanGroup
from spacy.util import filter_spans

Span.set_extension("value", default=None, force=True)

class RuleEngine:
    """
    Generic rule engine component.

    Config (per instance):

    - span_label: str                # span-group name e.g "weight"
    - entity_label: Optional[str]    # span label, e.g. "WEIGHT"
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

    def get_value_from_span(self, span, config):
        literal_value = config["literal_value"]
        value_matcher = config["value_matcher"]

        if literal_value is not None:
            return literal_value

        if not value_matcher:
            return None

        matches = value_matcher(span)
        values = []
        for _, s, e in matches:
            raw = span[s:e].text.replace(",", "")
            try:
                values.append(float(raw))
            except:
                values.append(raw)
        
        if not values:
            return None
        return max(values, key=lambda v: float(v) if isinstance(v, (int,float)) else -1)

    def find_spans(self, doc):
        spans = []
        for group_name, config in self.matchers.items():
            matcher = config.get("matcher")
            exclusion_matcher = config.get("exclusion")
            literal_value = config.get("literal_value")
            if literal_value is None:
                literal_value = group_name
            matches = matcher(doc)
            var_spans = []
            for _, s, e in matches:
                val = self.get_value_from_span(doc[s:e], config)
                if val is None:
                    val = literal_value
                sp = Span(doc, s, e, label=group_name)
                sp._.value = val
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