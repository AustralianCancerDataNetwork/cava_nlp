
from spacy.matcher import Matcher
from spacy.tokens import Span, Token
from spacy.util import filter_spans

class RuleEngine:
    """
    Generic rule engine component.

    Config (per instance):

    - token_label: str               # token-level boolean flag, e.g. "weight"
    - value_label: Optional[str]     # token-level numeric/string value, e.g. "weight_value"
    - entity_label: Optional[str]    # span label, e.g. "WEIGHT"
    - token_patterns: list           # spaCy Matcher patterns (outer list)
    - value_patterns: Optional[list] # patterns to extract numeric portion within span
    - norm_patterns: Optional[list]  # patterns to compute canonical NORM
    - exclusions: Optional[list]     # patterns to suppress spans
    - merge_ents: bool               # whether to merge matched span into a single token
    - debug: bool                    # whether to log rule activity to doc._.rule_debug
    """
    def __init__(self, nlp, name, config):
        self.vocab = nlp.vocab
        self.name = name
        self.cfg = config

        # Labels & extensions
        self.token_label = config.get("token_label")
        self.value_label = config.get("value_label")
        self.entity_label = config.get("entity_label", "")
        self.merge_ents = config.get("merge_ents", False)

        # patterns
        self.token_patterns = config["token_patterns"]
        self.value_patterns = config.get("value_patterns")
        self.norm_patterns = config.get("norm_patterns")
        self.exclusion_patterns = config.get("exclusions")

        # matchers
        self.matcher = Matcher(self.vocab)
        self.matcher.add(self.token_label, self.token_patterns)

        self.value_matcher = None
        if self.value_patterns:
            self.value_matcher = Matcher(self.vocab)
            self.value_matcher.add(self.value_label, self.value_patterns)

        self.norm_matcher = None
        if self.norm_patterns:
            self.norm_matcher = Matcher(self.vocab)
            self.norm_matcher.add("norm_match", self.norm_patterns)

        self.exclusion_matcher = None
        if self.exclusion_patterns:
            self.exclusion_matcher = Matcher(self.vocab)
            self.exclusion_matcher.add("exclude", self.exclusion_patterns)

        # Set token extensions
        Token.set_extension(self.token_label, default=False, force=True)
        if self.value_label:
            Token.set_extension(self.value_label, default=None, force=True)

    def find_spans(self, doc):
        matches = self.matcher(doc)
        spans = [Span(doc, s, e, label=self.entity_label) for _, s, e in matches]
        spans = filter_spans(spans)

        # apply exclusions
        if self.exclusion_matcher:
            excl = self.exclusion_matcher(doc)
            excl_spans = [Span(doc, s, e) for _, s, e in excl]
            spans = [sp for sp in spans if not any(
                sp.start_char >= ex.start_char and sp.end_char <= ex.end_char
                for ex in excl_spans
            )]
        return spans
    
    def extract_value(self, span):
        if not self.value_matcher:
            return None

        matches = self.value_matcher(span)
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

    def extract_norm(self, span):
        if not self.norm_matcher:
            return span.text.lower()

        matches = self.norm_matcher(span)
        parts = [span[s:e].text for _, s, e in matches]
        return "".join(parts).lower()

    def __call__(self, doc):
        spans = self.find_spans(doc)

        with doc.retokenize() as retok:
            for sp in spans:
                value = self.extract_value(sp)
                norm = self.extract_norm(sp)

                retok.merge(sp, attrs={"NORM": norm})

                for tok in sp:
                    tok._.set(self.token_label, True)
                    if self.value_label:
                        tok._.set(self.value_label, value)

                if self.entity_label:
                    doc.ents += (Span(doc, sp.start, sp.end, label=self.entity_label),)
        return doc