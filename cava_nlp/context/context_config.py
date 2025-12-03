from medspacy.context import DEFAULT_ATTRIBUTES
from pathlib import Path
import spacy

def get_context_attrs():
    # register new attribute used to mark when there is an explicit notation of currency e.g. 'on examination:' or 'currently ... '
    spacy.tokens.Span.set_extension('is_current', default=False, force=True)
    spacy.tokens.Span.set_extension('date_of', default=False, force=True)
    DEFAULT_ATTRIBUTES['CURRENT'] = {'is_current': True}
    DEFAULT_ATTRIBUTES['DATEOF'] = {'date_of': True}
    return DEFAULT_ATTRIBUTES

def get_context_patterns():
    return Path(__file__).resolve().parent / '_context_config.json'
    