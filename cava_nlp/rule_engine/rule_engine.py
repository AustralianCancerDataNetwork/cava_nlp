
from spacy.matcher import Matcher
from spacy.tokens import Span, Doc, SpanGroup
from spacy.util import filter_spans
from spacy.language import Language
from dataclasses import dataclass
from .value_resolver import (CASTERS, AGGREGATORS, ValueResolver)
from ..namespaces.core.rule_config import RuleEngineConfig

from typing import Any, Dict, List, TypeAlias, Optional, cast

SpacyTokenPattern: TypeAlias = Dict[str, Any]
SpacyMatcherPatterns: TypeAlias = List[List[SpacyTokenPattern]]

@dataclass(frozen=True)
class MatcherConfig:
    matcher: Matcher
    literal_value: Optional[Any]
    value_matcher: Optional[Matcher]
    exclusion: Optional[Matcher]

Span.set_extension("value", default=None, force=True)


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end

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

    def _build_matchers(self) -> None:
        for name, pat in self.cfg.patterns.items():
            token_matcher = Matcher(self.vocab)

            token_patterns = cast(
                SpacyMatcherPatterns,
                pat.token_patterns,
            )
            token_matcher.add(name, token_patterns)

            value_matcher = None
            if pat.value_patterns is not None:
                value_matcher = Matcher(self.vocab)
                value_patterns = cast(
                    SpacyMatcherPatterns,
                    pat.value_patterns,
                )
                value_matcher.add(
                    f"{self.span_label}_value",
                    value_patterns
                )

            exclusion_matcher = None
            if pat.exclusions is not None:
                exclusion_matcher = Matcher(self.vocab)
                exclusion_patterns = cast(
                    SpacyMatcherPatterns,
                    pat.exclusions,
                )
                exclusion_matcher.add(
                    f"{self.span_label}_exclusion",
                    exclusion_patterns
                )

            self.matchers[name] = MatcherConfig(
                matcher=token_matcher,
                literal_value=pat.value,
                value_matcher=value_matcher,
                exclusion=exclusion_matcher,
            )


    def __init__(
            self, 
            nlp: Language, 
            name: str, 
            config: RuleEngineConfig,
        ) -> None:
        
        """
        Create a rule-based extraction component.

        Parameters
        ----------
        nlp : Language
            The spaCy Language object. Used to access the vocabulary
            and to construct matchers.
        name : str
            Name of this rule engine instance (pipeline component name).
        config : Mapping[str, Any]
            Configuration dictionary, typically loaded from YAML/JSON.

        Expected config structure:

        {
            "span_label": str,
            "entity_label": Optional[str],
            "value_type": Optional[str],
            "value_aggregation": Optional[str],
            "merge_ents": Optional[bool],
            "patterns": {
                "<pattern_name>": {
                    "token_patterns": list,
                    "value": Optional[Any],
                    "value_patterns": Optional[list],
                    "exclusions": Optional[list],
                }
            }
        }
        """

        self.vocab = nlp.vocab
        self.name = name
        self.cfg = config

        self.span_label = config.span_label
        self.entity_label = config.entity_label
        self.merge_ents = config.merge_ents
        self.resolver = ValueResolver(
            caster=CASTERS.get(config.value_type, CASTERS["str"]),
            aggregator=AGGREGATORS.get(
                config.value_aggregation,
                AGGREGATORS["first"],
            ),
        )

        Span.set_extension(self.span_label, default=None, force=True)

        self.matchers: dict[str, MatcherConfig] = {}
        self._build_matchers()


    def _extract_raw_values(
        self,
        span: Span,
        matcher: Optional[Matcher],
    ) -> list[Span]:        
        if not matcher:
            return []
        matches = matcher(span)
        raw: List[Span] = []
        for _, s, e in matches:
            raw.append(span[s:e])
        return filter_spans(raw)
    
    def _trim_punct_edges(self, sp: Span) -> Span | None:
        """
        Remove leading and trailing punctuation tokens from a span.
        Returns None if no tokens remain.

        Assumption: Punctuation is never semantic at the span boundary.
        Impact: Significantly more likely to be a context factor match - 
        we only want the core text, and internal punctionation if any.
        """
        start, end = sp.start, sp.end

        # Trim leading punctuation
        while start < end and sp.doc[start].is_punct:
            start += 1

        # Trim trailing punctuation
        while end > start and sp.doc[end - 1].is_punct:
            end -= 1

        if start >= end:
            return None

        return Span(sp.doc, start, end, label=sp.label)


    def find_spans(self, doc: Doc) -> list[Span]:
        collected: list[Span] = []

        for group_name, cfg in self.matchers.items():
            for _, start, end in cfg.matcher(doc):
                sp = Span(doc, start, end, label=group_name)
                sp = self._trim_punct_edges(sp)
                if sp is None:
                    continue
                if cfg.exclusion is not None:
                    if any(
                        overlaps(start, end, ex_start, ex_end)
                        for _, ex_start, ex_end in cfg.exclusion(doc)
                    ):
                        continue

                if cfg.literal_value is not None:
                    value = cfg.literal_value
                else:
                    raw_values = (
                        self._extract_raw_values(sp, cfg.value_matcher)
                        if cfg.value_matcher is not None
                        else []
                    )
                    value = self.resolver.resolve(raw_values)

                sp._.value = value
                collected.append(sp)

        # De-overlap across all rule groups
        return filter_spans(collected)

    def __call__(self, doc: Doc) -> Doc:
        spans = self.find_spans(doc)

        if self.span_label not in doc.spans:
            doc.spans[self.span_label] = SpanGroup(doc)
        group = cast(SpanGroup, doc.spans[self.span_label])
                
        with doc.retokenize() as retok:
            for sp in spans:
                if self.merge_ents:
                    retok.merge(sp)        
                group.append(sp)
                if self.entity_label:
                    new_ent = Span(doc, sp.start, sp.end, label=self.entity_label)
                    doc.ents = tuple(doc.ents) + (new_ent,)
        return doc