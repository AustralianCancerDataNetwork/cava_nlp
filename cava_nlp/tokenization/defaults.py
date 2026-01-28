# type: ignore
import spacy
from spacy.lang.en import English
from spacy.language import Language
from spacy.tokenizer import Tokenizer
from typing import Dict, List, Callable, Iterable, Pattern
from spacy.util import compile_infix_regex, compile_prefix_regex, compile_suffix_regex
from .builder import build_cava_prefixes, build_cava_suffixes, build_cava_infixes
from .exceptions import (
    build_stage_exceptions,
    build_special_vocab_exceptions,
    build_clinical_symbol_exceptions,
    build_cycle_day_exceptions
)

def build_cava_exceptions(
        base_exceptions: Dict[str, List[Dict[str, str]]]
    ) -> Dict[str, List[Dict[str, str]]]:
    """
    Build ALL clinical/cancer-specific exceptions while removing irrelevant English exceptions.
    """

    # 1. Start with English defaults
    exc = {
        rule: case
        for rule, case in base_exceptions.items()
        # drop emoji-like and colon/equals prefixes
        if not rule.startswith((':', '='))
        # drop single-letter abbreviations like "p."
        if not (len(rule) == 2 and rule.endswith('.'))
    }
    exc.update(build_clinical_symbol_exceptions())
    exc.update(build_stage_exceptions())
    exc.update(build_special_vocab_exceptions())
    exc.update(build_cycle_day_exceptions())
    return exc


def create_cava_tokenizer(nlp: Language) -> Tokenizer:
    """
    Core tokenizer factory.
    Uses custom infix/prefix/suffix and pruned exceptions.
    """
    prefixes = compile_prefix_regex(nlp.Defaults.prefixes).search
    suffixes = compile_suffix_regex(nlp.Defaults.suffixes).search
    infixes = compile_infix_regex(nlp.Defaults.infixes).finditer

    return Tokenizer(
        nlp.vocab,
        nlp.Defaults.tokenizer_exceptions,
        prefix_search=prefixes,
        suffix_search=suffixes,
        infix_finditer=infixes,
        token_match=nlp.Defaults.token_match,
        url_match=nlp.Defaults.url_match,
    )


class CaVaLangDefaults(English.Defaults):
    """
    Defaults for CaVaLang, with:
    - pruned special cases
    - brutal infix/prefix/suffix splitting
    - URL recognition disabled
    """

    tokenizer_exceptions: dict[str, list[dict[str, str]]] = (
        build_cava_exceptions(English.Defaults.tokenizer_exceptions)
    )

    prefixes: Iterable[str | Pattern[str]] = build_cava_prefixes()
    suffixes: Iterable[str | Pattern[str]] = build_cava_suffixes()
    infixes: Iterable[str | Pattern[str]] = build_cava_infixes()


    url_match: Callable[[str], bool] | None = None
    create_tokenizer: Callable[[Language], Tokenizer] = create_cava_tokenizer