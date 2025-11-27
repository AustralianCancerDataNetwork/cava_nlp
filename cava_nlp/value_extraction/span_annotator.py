import spacy
from spacy.tokens import Doc, Token
from spacy.language import Language


Token.set_extension("span_head", default=False, force=True)
Token.set_extension("inside_span", default=False, force=True)
Token.set_extension("span_label", default=None, force=True)
Token.set_extension("span_len", default=0, force=True)
Token.set_extension("span_index", default=None, force=True)
Token.set_extension("norm_value", default=None, force=True)

# Generic flags for semantic classes (you can extend these)
Token.set_extension("decimal", default=False, force=True)
Token.set_extension("date", default=False, force=True)
Token.set_extension("sci_not", default=False, force=True)
Token.set_extension("time", default=False, force=True)
Token.set_extension("unit_value", default=False, force=True)
Token.set_extension("ecog_value", default=False, force=True)
Token.set_extension("range_part", default=False, force=True)

LABEL_FLAG_MAP = {
    "DATE": "date",
    "DECIMAL": "decimal",
    "SCI_NOT": "sci_not",
    "TIME": "time",
    "UNIT_VALUE": "unit_value",
    "ECOG": "ecog_value",
}

class SpanAnnotator:
    """
    Converts spans in doc.spans[...] into stable token-level flags
    that allow downstream spaCy Matchers to treat multi-token spans as
    single semantic units (via span_head=True & span_len, span_label, etc.).

    This solves the multi-token span problem WITHOUT retokenisation.
    """

    def __init__(self, nlp, span_groups=None):
        """
        span_groups: list of keys in doc.spans to annotate (e.g. ["DATES","DECIMALS"])
                        If None: annotate ALL span groups.
        """
        self.span_groups = span_groups

    def __call__(self, doc):

        if self.span_groups is None:
            groups = doc.spans.keys()
        else:
            groups = self.span_groups

        for group_name in groups:
            spans = doc.spans.get(group_name, [])
            for span in spans:
                self._annotate_span(span, group_name)

        return doc

    def _apply_head_flags(self, head, label, span_len):
        head._.span_head = True
        head._.span_label = label
        head._.span_len = span_len
        head._.span_index = 0

        # Apply semantic class flags using map
        ulabel = label.upper()
        for key, flag in LABEL_FLAG_MAP.items():
            if key in ulabel:
                setattr(head._, flag, True)

    def _apply_child_flags(self, span, label, span_len):
        for i, tok in enumerate(span):
            tok._.inside_span = True
            tok._.span_label = label    
            tok._.span_index = i
            tok._.span_len = span_len

    def _annotate_span(self, span, group_name):
        """
        Annotate all tokens in the span with flags and metadata:
        - mark head token
        - mark children
        - set semantic class flags
        """
        label = span.label_ or group_name
        self._apply_head_flags(span[0], label, len(span))
        self._apply_child_flags(span, label, len(span))
        self._attach_norm_value(span)

    def _attach_norm_value(self, span):
        """
        Example heuristic: attempt to normalize numeric spans.
        Extend this for units, ECOG ranges, decimals, sci_not, etc.
        """

        text = span.text.strip()

        # numeric
        if text.replace(".", "", 1).isdigit():
            try:
                span[0]._.norm_value = float(text)
                return
            except:
                pass

        # zero / o / zero-like
        if text.lower() in ("o", "zero"):
            span[0]._.norm_value = 0
            return

        # Extend with domain-specific norms here (dates, ranges, sci_not, etc.)
        return


@Language.factory("cava_span_annotator")
def build_span_annotator(nlp, name):
    return SpanAnnotator(nlp.vocab)
