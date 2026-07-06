import re
from spacy.lang.en import English
from spacy.tokens import Doc
from typing import Any
from spacy.util import registry

# unused imports required to register components
from . import sentence_splitting

from .tokenization.defaults import CaVaLangDefaults
from .tokenization.preprocess import whitespace_preprocess

@registry.languages('cava_lang')
class CaVaLang(English):
    lang = "cava_lang"
    Defaults = CaVaLangDefaults

    def __init__(
            self, 
            with_section_context: bool=False, 
            with_dated_section_context: bool=False, 
            *args: Any, 
            **kwargs: Any
        ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[reportUnknownMemberType]

        # Start with spaCy-native splitting and add line-oriented clinical rules.
        self.add_pipe("cava_sentencizer")

    def __call__(
            self, 
            text: str, 
            whitespace_strip: tuple[str,str]=(' ', '\n'), 
            *args: Any, 
            **kwargs: Any
        ) -> Doc:
        # Whitespace preprocessing (optional)
        if whitespace_strip:
            text = whitespace_preprocess(text, whitespace_strip)

        # Mask emails before tokenization if needed
        email_regex = r"[A-Za-z0-9.\-_]+@[A-Za-z0-9\-.]+\.[A-Za-z]+"
        text = re.sub(email_regex, lambda m: "x" * len(m.group()), text)

        return super().__call__(text, *args, **kwargs)
