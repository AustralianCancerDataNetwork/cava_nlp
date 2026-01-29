from spacy.matcher import Matcher
from spacy.util import filter_spans
from spacy.tokens import Token, Doc, Span, SpanGroup
from cava_nlp.namespaces.regex import (
    date_patterns,
    times,
    units_regex
)
import dateparser
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any

Token.set_extension("kind", default=None, force=True)

@dataclass
class NormalisationResult:
    """
    Structured output returned by all normaliser `compute()` methods.

    Attributes
    ----------
    norm : str
        The canonical string representation assigned as the token's ``NORM`` 
        attribute after merging. This replaces ``token.norm_`` for the merged span,
        enabling downstream components to work with a consistent, normalised textual
        representation (e.g., "5.4", "10^9", "2024-01-03").

    attrs : Dict[str, Any]
        A mapping of token extension names to values. These are written directly 
        into the merged token using::

            setattr(token._, ext_name, value)

        Examples include:
        - kind="decimal"
        - value=5.4
        - unit="kg"
        - date_obj=datetime(...)

        Because attrs is a free-form dictionary, each normaliser can specify 
        arbitrary structured metadata relevant to its domain.
    """
    norm: str
    attrs: Dict[str, Any] = field(default_factory=dict)

class BaseNormalizer:
    """
    Defines the interface and processing flow used by normalisation components. 
    
    Each subclass implements a spaCy ``Matcher`` and  ``compute()`` method to extracts 
    structured information from matched spans, plus optional token-level extensions.

    Methods
    -------
    compute(span) -> NormalisationResult
        Override to define how to normalise the matched span.

    get_spans(doc)
        Returns matched spans after filtering overlaps.

    apply(doc)
        Applies the normaliser to the document, merges spans, assigns NORM, and 
        populates token attributes from the compute() result.
    """

    NAME = None
    PATTERNS = []
    EXTENSIONS = []   

    def __init__(self, nlp):
        self.nlp = nlp
        self.matcher = Matcher(nlp.vocab)
        if self.NAME and self.PATTERNS:
            self.matcher.add(self.NAME, self.PATTERNS)
            Token.set_extension(self.NAME, default=False, force=True)

        for ext in self.EXTENSIONS:
            Token.set_extension(ext, default=None, force=True)

    def compute(self, span) -> NormalisationResult:
        """Override in subclass"""
        return NormalisationResult(norm=span.text)

    def get_spans(self, doc):
        matches = self.matcher(doc)
        spans = [doc[start:end] for _, start, end in matches]
        return filter_spans(spans)
    
    def apply(self, doc):
        """Run matcher on doc and merge spans."""
        spans = self.get_spans(doc)    
        if not spans:
            return doc

        matches = []
        for span in spans:
            res = self.compute(span)
            matches.append(
                {
                    "start_char": span.start_char,
                    "end_char": span.end_char,
                    "res": res,
                }
            )

        with doc.retokenize() as retok:
            for span, match in zip(spans, matches):
                res = match["res"]

                head = span[0]

                if hasattr(head._, "kind"):
                    head._.kind = self.NAME

                for attr, val in res.attrs.items():
                    setattr(head._, attr, val)

                setattr(head._, self.NAME, True)  # type: ignore
                retok.merge(span, attrs={"NORM": res.norm})
        return doc
    

class DecimalNormalizer(BaseNormalizer):
    """
    This is required because of the harsh tokenization in this pipeline - otherwise would be core spaCy functionality.
    "Temp is 36.9 today" 
        token ["36.9"] norm="36.9", value=36.9, kind="decimal"
    """
    NAME = "decimal"
    EXTENSIONS = ["value"]
    PATTERNS = [
            [ 
                # strict about trailing spaces for reassembling decimal points
                {"IS_DIGIT": True, "LIKE_NUM": True, "SPACY": False}, 
                {"ORTH": {"IN": ['.']}, 'SPACY': False}, 
                {"IS_DIGIT": True, "LIKE_NUM": True}
            ]
        ]

    def compute(self, span):
        text = span.text.replace(",", ".")
        value = float(text)
        return NormalisationResult(
            norm=text,
            attrs={
                "value": value
            }
        )

class BulletNormalizer(BaseNormalizer):
    NAME = "bullet"
    EXTENSIONS = ["is_bullet"]
    SYMBOL_BULLET = [
        {
            "IS_SENT_START": True,
            "TEXT": {"IN": ["-", "•", "*", "–", "—"]}
        },
    ]
    SIMPLE_ENUMERATOR = [
        {
            "IS_SENT_START": True,
            "TEXT": {"REGEX": r"^[0-9a-zA-Z]+$"}
        },
        {
            "TEXT": {"IN": [".", ")"]},
        },
    ]
    PAREN_ENUMERATOR = [
        {
            "IS_SENT_START": True,
            "ORTH": "("
        },
        {"TEXT": {"REGEX": r"^[0-9a-zA-Z]+$"}},
        {"ORTH": ")"},
    ]
    PATTERNS = [SYMBOL_BULLET, SIMPLE_ENUMERATOR, PAREN_ENUMERATOR]


    def compute(self, span):
        text = span.text
        return NormalisationResult(
            norm=text,
            attrs={"is_bullet": True}
        )

class SciNotNormalizer(BaseNormalizer):
    """
    "WCC was 10^9 today"
        token ["10^9"], norm="10.0^9", value=1_000_000_000, kind="scientific", base=10.0, exp=9
    """    
    NAME = "scientific"
    EXTENSIONS = ["value", "base", "exp"]
    PATTERNS = [
            [
                {"LOWER":"x", "OP": "?"},
                {"TEXT": "10"}, 
                {"LOWER":"x", "OP": "?"},
                {"TEXT": {"IN":["^", "**"]}},
                {"IS_DIGIT": True}
            ],
            [
                {"IS_DIGIT": True, 'SPACY': False},
                {"LOWER": "e", 'SPACY': False},
                {"TEXT": "+", "OP": "?"},
                {"IS_DIGIT": True}
            ]
        ]
    
    def compute(self, span):
        try:
            base = float([t.text for t in span if t.like_num][0])
            raw_exp = span[-1].text.replace("^", "").replace("**", "")
            exp = int(raw_exp)
            value = base ** exp
        except Exception:
            return NormalisationResult(
                norm=span.text,
                attrs={}
            )
        return NormalisationResult(
            norm=f"{base}^{exp}",
            attrs={
                "base": base,
                "exp": exp,
                "value": value
            }
        )


class DateNormalizer(BaseNormalizer):
    NAME = "date"
    EXTENSIONS = ["value"]

    def __init__(self, nlp):
        self.skip_matcher = Matcher(nlp.vocab)   # handles sentence-start patterns
        self._register_patterns()
        super().__init__(nlp)

    def patterns(self):
        dp = [[],[]] # dates must either start sentence or have preceding space, to avoid false pos with spinal notation e.g. C3/4
        for d in date_patterns:
            dp[0].append([{"SPACY": True}] + d)
            dp[0].append([{"TEXT": {"IN": ["\n", "\n\n", '-']}}] + d)
            sent_start = [attr.copy() for attr in d]
            sent_start[0]["IS_SENT_START"] = True
            dp[1].append(sent_start)
        return dp
    
    def _register_patterns(self):
        patterns = self.patterns()
        assert len(patterns) == 2, "DateNormalizer patterns should return two lists."
        self.skip_matcher.add(self.NAME, patterns[0])
        self.PATTERNS = patterns[1]

    def get_spans(self, doc):
        matches = self.matcher(doc)
        spans = [doc[start:end] for _, start, end in matches]
        skip_matches = self.skip_matcher(doc)
        spans += [doc[start+1:end] for _, start, end in skip_matches]
        return filter_spans(spans)
    
    def compute(self, span):
        try:
            dt = datetime.strptime(span.text, "%Y-%m-%d")
        except ValueError:
            # todo: make this configurable for non-au users
            dt = dateparser.parse(span.text, settings={'DATE_ORDER': 'DMY', "PREFER_DAY_OF_MONTH": 'first'})
        norm=dt.strftime("%Y-%m-%d") if dt else span.text
        return NormalisationResult(
            norm=norm,
            attrs={"value": norm}
        )
    


TIME_FORMATS = [
    "%H:%M",       # 07:30
    "%I:%M%p",     # 7:30pm
    "%I%p",        # 7pm
    "%H%M",        # 1330
]

def parse_single_time(text: str):
    """
    Try strict time parsing first, then fallback to dateparser.
    Return a datetime or None.
    """
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    
    # fallback: let dateparser guess time
    dt = dateparser.parse(
        text,
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "UTC",
            "RETURN_AS_TIMEZONE_AWARE": False
        },
    )
    return dt

def normalize_time(text: str):
    """
    Convert text to canonical HH:MM (24h).
    Return None if failed.
    """
    dt = parse_single_time(text)
    if not dt:
        return None
    return dt.strftime("%H:%M")

class TimeNormalizer(BaseNormalizer):
    NAME = "time"
    EXTENSIONS = ["value"]   

    PATTERNS = [
        [  
            {"LIKE_NUM": True},
            {"LOWER": {"IN": [t.lower() for t in times]}},
        ],
        [
            {"LIKE_NUM": True},
            {"TEXT": {"IN": [":"]}},
            {"LIKE_NUM": True},
            {"LOWER": {"IN": [t.lower() for t in times]}},
        ],
        [
            {"LOWER": {"IN": [str(t) for t in range(24)]}},
            {"TEXT": {"IN": [":"]}},
            {"TEXT": {"REGEX": r"^[0-5][0-9]$"}},
            {"TEXT": {"IN": [":"]}, "OP": "?"},
            {"TEXT": {"REGEX": r"^[0-5][0-9]$"}, "OP": "?"},
        ]
    ]

    def compute(self, span):
        norm = normalize_time(span.text)
        if not norm:
            return NormalisationResult(
                norm=span.text,
                attrs={"value": span.text},
            )
        
        return NormalisationResult(
            norm=norm,
            attrs={"value": norm},
        )
    
class UnitNormalizer(BaseNormalizer):
    NAME = "unit_norm"
    EXTENSIONS = ["value", "unit"]
    PATTERNS = [
            [
                {"LIKE_NUM": True},
                {"LOWER": {"REGEX": units_regex}},
            ],
            [
                {"LIKE_NUM": True},
                {"LOWER": {"REGEX": units_regex}},
                {"TEXT": "/"},
                {"LIKE_NUM": True, "OP": "?"},
                {"LOWER": {"REGEX": units_regex}},
            ]
        ]

    def compute(self, span):
        text = span.text.lower()
        # There will always be a number at the start due to the pattern
        try:
            value = float(span[0].text)
            unit_part = span[1:].text.lower() 
        except ValueError:
            value = None
            unit_part = text

        return NormalisationResult(
            norm=text,   # normalized join of everything
            attrs={
                "value": value,
                "unit": unit_part
            }
        )
    
class RangeNormalizer(BaseNormalizer):
    """
    Normalizes numeric ranges like:
        1-2
        3–5

    Excludes dates because DateNormalizer runs first.
    """
    NAME = "range"
    EXTENSIONS = ["value", "low", "high"]

    PATTERNS = [
        [
            {
                "LIKE_NUM": True, 
                "SPACY": False},
            {
                "TEXT": {"IN": ["-", "–", "—"]},
                "SPACY": False
            },
            {
                "LIKE_NUM": True
            },
        ],
        [
            {"LIKE_NUM": True},
            {
                "TEXT": {"IN": ["to"]},
            },
            {"LIKE_NUM": True},
        ],
    ]

    def compute(self, span):
        try:
            low = float(span[0].text)
            high = float(span[-1].text)
        except ValueError:
            return NormalisationResult(norm=span.text)

        return NormalisationResult(
            norm=f"{low}-{high}",
            attrs={
                "value": [low, high],
                "low": low,
                "high": high,
            }
        )


class ClinicalNormalizer:
    def __init__(self, nlp):
        self.normalizers = [
            DateNormalizer(nlp),
            DecimalNormalizer(nlp),
            SciNotNormalizer(nlp),
            TimeNormalizer(nlp),
            UnitNormalizer(nlp),
            RangeNormalizer(nlp),
            BulletNormalizer(nlp),
        ]

    def create_span_groups(self, doc):
        groups = {}
        for token in doc:
            if token._.kind:
                label = token._.kind
                sp = Span(doc, token.i, token.i+1, label=label)
                groups.setdefault(label, []).append(sp)
        for label, spans in groups.items():
            doc.spans[label] = SpanGroup(doc, spans=spans)

    def __call__(self, doc):
        for norm in self.normalizers:
            doc = norm.apply(doc)
        self.create_span_groups(doc)
        return doc


