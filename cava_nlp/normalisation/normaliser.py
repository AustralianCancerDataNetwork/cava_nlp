from spacy.matcher import Matcher
from spacy.util import filter_spans
from spacy.tokens import Token
from cava_nlp.regex import (
    date_patterns,
    times,
    units_regex
)
import dateparser

Token.set_extension("value", default=None)
Token.set_extension("kind", default=None)
Token.set_extension("unit_num", default=None)
Token.set_extension("unit_den", default=None)

class BaseNormalizer:

    def __init__(self, nlp):
        self.nlp = nlp
        self.matcher = Matcher(nlp.vocab)
        self._register_patterns()

    def _register_patterns(self):
        patterns = self.patterns()
        if patterns:
            self.matcher.add(self.__class__.__name__, patterns)

    def patterns(self):
        """Return a list of spaCy matcher patterns."""
        return []

    def norm(self, span):
        """Return NORM string. Override."""
        return span.text

    def extend(self, token, norm_value):
        """Set custom attributes on a merged token."""
        pass

    def get_spans(self, doc):
        matches = self.matcher(doc)
        spans = [doc[start:end] for _, start, end in matches]
        return filter_spans(spans)
    
    def apply(self, doc):
        """Run matcher on doc and merge spans."""
        spans = self.get_spans(doc)    
        if not spans:
            return doc

        with doc.retokenize() as retok:
            for span in spans:
                norm_val = self.norm(span)
                retok.merge(span, attrs={"NORM": norm_val})
                token = doc[span.start]
                self.extend(token, norm_val)

        return doc

class DecimalNormalizer(BaseNormalizer):
    def patterns(self):
        return [
            [
                {"IS_DIGIT": True, "LIKE_NUM": True}, 
                {"ORTH": {"IN": ['.', ',']}, 'SPACY': False}, 
                {"IS_DIGIT": True, "LIKE_NUM": True}
            ]
        ]

    def norm(self, span):
        return span.text.replace(",", ".")

    def extend(self, token, norm_value):
        token._.kind = "decimal"
        token._.value = float(norm_value)

class SciNotNormalizer(BaseNormalizer):
    def patterns(self):
        return [
            [
                {"LOWER":"x", "OP": "?"},
                {"TEXT": "10"}, 
                {"LOWER":"x", "OP": "?"},
                {"TEXT": {"IN":["^", "**"]}},
                {"IS_DIGIT": True}
            ],
            [
                {"IS_DIGIT": True},
                {"LOWER": "e"},
                {"TEXT": "+", "OP": "?"},
                {"IS_DIGIT": True}
            ]
        ]

    def norm(self, span):
        base = float([t.text for t in span if t.like_num][0])
        exp = int(span[-1].text.lstrip("^").lstrip("**"))
        return f"{base}^{exp}"

    def extend(self, token, norm_value):
        base, exp = norm_value.split("^")
        token._.kind = "scientific"
        token._.value = float(base) ** int(exp)


class DateNormalizer(BaseNormalizer):

    def __init__(self, nlp):
        self.skip_matcher = Matcher(nlp.vocab)
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
        self.skip_matcher.add(self.__class__.__name__, patterns[1])
        self.matcher.add(self.__class__.__name__, patterns[0])

    def get_spans(self, doc):
        matches = self.matcher(doc)
        spans = [doc[start:end] for _, start, end in matches]
        skip_matches = self.skip_matcher(doc)
        spans += [doc[start+1:end] for _, start, end in skip_matches]
        return filter_spans(spans)
    
    def norm(self, span):
        try:
            dt = dateparser.parse(span.text, settings={'PREFER_DAY_OF_MONTH': 'first'})
            if dt:
                return dt.strftime("%Y-%m-%d")
        except Exception:
            return span.text

    def extend(self, token, norm_value):
        token._.kind = "date"


class TimeNormalizer(BaseNormalizer):

    def patterns(self):
        TIMES = [t.lower() for t in times]
        return [
            [
                {"LIKE_NUM": True},
                {"LOWER": {"IN": TIMES}},
            ]
        ]

    def extend(self, token, norm_value):
        token._.kind = "time"


class UnitNormalizer(BaseNormalizer):

    merge = True

    def patterns(self):
        return [
            [
                {"LIKE_NUM": True},
                {"LOWER": {"REGEX": units_regex}},
            ],
            [
                {"LOWER": {"REGEX": units_regex}},
                {"TEXT": "/"},
                {"LOWER": {"REGEX": units_regex}},
            ],
            [
                {
                    "TEXT": {"REGEX": r"^[A-Za-z]+/[A-Za-z0-9\^]+$"}
                }
            ],
        ]

    def norm(self, span):
        return "".join(t.text for t in span).replace(" ", "").lower()

    def extend(self, token, norm_value):
        token._.kind = "unit"
        if "/" in norm_value:
            token._.unit_num, token._.unit_den = norm_value.split("/", 1)
        else:
            token._.unit_num = norm_value
            token._.unit_den = None


class ClinicalNormalizer:
    def __init__(self, nlp):
        self.normalizers = [
            DecimalNormalizer(nlp),
            SciNotNormalizer(nlp),
            DateNormalizer(nlp),
            TimeNormalizer(nlp),
            UnitNormalizer(nlp)
        ]

    def __call__(self, doc):
        for norm in self.normalizers:
            doc = norm.apply(doc)
        return doc
