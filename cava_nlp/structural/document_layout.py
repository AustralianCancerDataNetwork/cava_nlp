from spacy.language import Language
from spacy.tokens import Doc, Span
from typing import Optional
from spacy.tokens import Token


def first_non_space_token(span: Span) -> Optional[Token]:
    for tok in span:
        if not tok.is_space:
            return tok
    return None


class DocumentLayout:

    def __init__(self, nlp: Language, name: str):
        self.nlp = nlp
        self.name = name

    def __call__(self, doc: Doc) -> Doc:
        # if there are no sentences, return early
        try:
            next(doc.sents)
        except StopIteration:
            return doc

        parentheticals: list[tuple[int, int]] = []
        list_items: list[tuple[int, int]] = []

        for sent in doc.sents:
            
            stack: list[int] = []

            for tok in sent:
                if tok.text == "(":
                    stack.append(tok.i)
                elif tok.text == ")" and stack:
                    start = stack.pop()
                    parentheticals.append((start, tok.i + 1))
                    # correctly ignores unmatched '()'
            
            first_tok = first_non_space_token(sent)
            if first_tok and getattr(first_tok._, "is_bullet", False):
                list_items.append((sent.start, sent.end))

        doc._.parentheticals = parentheticals
        doc._.list_items = list_items
        return doc
