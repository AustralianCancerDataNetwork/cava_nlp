from spacy.language import Language

from collections.abc import Iterable

from .config import DEFAULT_SENTENCE_SPLITTING_CONFIG
from .sentencizer import CavaSentencizer


@Language.factory(
    "cava_sentencizer",
    default_config=DEFAULT_SENTENCE_SPLITTING_CONFIG,
)
def create_cava_sentencizer(
    nlp: Language,
    name: str,
    punct_chars: Iterable[str] | None = None,
    abbreviation_tokens: Iterable[str] = (),
    newline_boundaries: bool = True,
) -> CavaSentencizer:
    if not abbreviation_tokens:
        abbreviation_tokens = DEFAULT_SENTENCE_SPLITTING_CONFIG["abbreviation_tokens"]
    return CavaSentencizer(
        nlp=nlp,
        name=name,
        punct_chars=punct_chars,
        abbreviation_tokens=abbreviation_tokens,
        newline_boundaries=newline_boundaries,
    )
