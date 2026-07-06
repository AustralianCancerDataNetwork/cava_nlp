from collections.abc import Iterable

from spacy.language import Language
from spacy.pipeline import Sentencizer
from spacy.tokens import Doc, Token

from .config import DEFAULT_ABBREVIATIONS


def _previous_non_space(doc: Doc, start: int) -> Token | None:
    for i in range(start - 1, -1, -1):
        if not doc[i].is_space:
            return doc[i]
    return None


def _next_non_space(doc: Doc, start: int) -> Token | None:
    for i in range(start + 1, len(doc)):
        if not doc[i].is_space:
            return doc[i]
    return None


class CavaSentencizer:
    """
    Sentence segmentation tuned for line-oriented clinical text.

    This starts with spaCy's native punctuation-based sentencizer, then:
    - shifts sentence starts off whitespace tokens so newlines stay attached
      to the preceding sentence;
    - treats newline-delimited clinical lines as sentence starts;
    - suppresses false splits after short clinical abbreviations such as
      ``p. 55`` and dotted letter sequences such as ``i.v.``.
    """

    def __init__(
        self,
        nlp: Language,
        name: str,
        punct_chars: Iterable[str] | None = None,
        abbreviation_tokens: Iterable[str] = DEFAULT_ABBREVIATIONS,
        newline_boundaries: bool = True,
    ) -> None:
        self.nlp = nlp
        self.name = name
        self.newline_boundaries = newline_boundaries
        self.abbreviation_tokens = {token.lower() for token in abbreviation_tokens}
        self.sentencizer = Sentencizer(
            name=f"{name}_base",
            punct_chars=list(punct_chars) if punct_chars is not None else None,
            overwrite=True,
        )

    def __call__(self, doc: Doc) -> Doc:
        doc = self.sentencizer(doc)

        if not doc:
            return doc

        doc[0].is_sent_start = True
        self._shift_whitespace_starts(doc)

        if self.newline_boundaries:
            self._apply_newline_boundaries(doc)

        self._suppress_abbreviation_splits(doc)
        return doc

    def _shift_whitespace_starts(self, doc: Doc) -> None:
        for token in doc:
            if not (token.is_space and token.is_sent_start):
                continue
            next_token = _next_non_space(doc, token.i)
            token.is_sent_start = False
            if next_token is not None:
                next_token.is_sent_start = True

    def _apply_newline_boundaries(self, doc: Doc) -> None:
        for token in doc:
            if not (token.is_space and "\n" in token.text):
                continue
            next_token = _next_non_space(doc, token.i)
            if next_token is not None:
                next_token.is_sent_start = True

    def _suppress_abbreviation_splits(self, doc: Doc) -> None:
        for token in doc[1:]:
            if not token.is_sent_start:
                continue

            boundary = _previous_non_space(doc, token.i)
            if boundary is None or boundary.text != ".":
                continue

            head = _previous_non_space(doc, boundary.i)
            if head is None:
                continue

            head_text = head.text.rstrip(".").lower()
            if head_text in self.abbreviation_tokens:
                token.is_sent_start = False
                continue

            if len(head_text) == 1 and head_text.isalpha():
                if token.like_num or token.is_lower or (len(token.text) == 1 and token.is_alpha):
                    token.is_sent_start = False
