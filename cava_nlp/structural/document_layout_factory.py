from spacy.language import Language
from spacy.tokens import Doc, Token
from .document_layout import DocumentLayout

@Language.factory("document_layout")
def create_document_layout(nlp: Language, name: str) -> DocumentLayout:
    if not Doc.has_extension("parentheticals"):
        Doc.set_extension("parentheticals", default=[])
    if not Doc.has_extension("list_items"):
        Doc.set_extension("list_items", default=[])
    if not Token.has_extension("is_bullet"):
        Token.set_extension("is_bullet", default=False)
    if not Token.has_extension("bullet_type"):
        Token.set_extension("bullet_type", default=None)
    return DocumentLayout(nlp, name)