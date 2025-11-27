import re
import spacy
from spacy.language import Language
from spacy.lang.en import English

from .tokenization.defaults import CaVaLangDefaults
from .tokenization.preprocess import whitespace_preprocess


@spacy.registry.languages('cava_lang')
class CaVaLang(English):
    lang = "cava_lang"
    Defaults = CaVaLangDefaults

    def __init__(self, with_section_context=False, with_dated_section_context=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use medSpaCy sentencizer - todo: this is better than pyrush for newlines but brings a python <3.12 dependency for pep701
        self.add_pipe("medspacy_pysbd")

        # Optional: sectionizers
        if with_section_context or with_dated_section_context:
            from .sectioning import (
                get_sectionizer_attrs, 
                get_sectionizer_patterns, 
                get_dated_sectionizer_patterns,
                get_context_attrs,
                get_context_patterns,
            )

            sectionizer_config = {
                "rules": None,
                "span_attrs": get_sectionizer_attrs(),
            }
            sectionizer_type = (
                "dated_sectionizer" if with_dated_section_context else "medspacy_sectionizer"
            )
            sectionizer_patterns = (
                get_dated_sectionizer_patterns if with_dated_section_context else get_sectionizer_patterns
            )

            sectionizer = self.add_pipe(sectionizer_type, config=sectionizer_config)
            sectionizer.add(sectionizer_patterns())

            context = self.add_pipe(
                "medspacy_context",
                config={
                    "span_attrs": get_context_attrs(),
                    "rules": str(get_context_patterns()),
                },
            )

    def __call__(self, text, whitespace_strip=(' ', '\n'), *args, **kwargs):
        # Whitespace preprocessing (optional)
        if whitespace_strip:
            text = whitespace_preprocess(text, whitespace_strip)

        # Mask emails before tokenization if needed
        email_regex = r"[A-Za-z0-9.\-_]+@[A-Za-z0-9\-.]+\.[A-Za-z]+"
        text = re.sub(email_regex, lambda m: "x" * len(m.group()), text)

        return super().__call__(text, *args, **kwargs)
