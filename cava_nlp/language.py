import re
import spacy
from spacy.language import Language
from spacy.lang.en import English
from medspacy.sentence_splitting import PySBDSentenceSplitter

from .tokenization.defaults import CaVaLangDefaults
from .tokenization.preprocess import whitespace_preprocess

from spacy.util import registry

@registry.languages('cava_lang')
class CaVaLang(English):
    lang = "cava_lang"
    Defaults = CaVaLangDefaults

    def __init__(self, with_section_context=False, with_dated_section_context=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use medSpaCy sentencizer - todo: this is better than pyrush for newlines but brings a python <3.12 dependency for pep701
        self.add_pipe("medspacy_pysbd")

    def __call__(self, text, whitespace_strip=(' ', '\n'), *args, **kwargs):
        # Whitespace preprocessing (optional)
        if whitespace_strip:
            text = whitespace_preprocess(text, whitespace_strip)

        # Mask emails before tokenization if needed
        email_regex = r"[A-Za-z0-9.\-_]+@[A-Za-z0-9\-.]+\.[A-Za-z]+"
        text = re.sub(email_regex, lambda m: "x" * len(m.group()), text)

        return super().__call__(text, *args, **kwargs)
