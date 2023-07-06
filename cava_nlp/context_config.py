from medspacy.context import DEFAULT_ATTRIBUTES
from pathlib import Path

def get_context_attrs():
    # register new attribute used to mark when there is an explicit notation of currency e.g. 'on examination:' or 'currently ... '
    try:
        spacy.tokens.Span.set_extension('is_current', default=False)
    except:
        ... # already registered
    DEFAULT_ATTRIBUTES['CURRENT'] = {'is_current': True}
    return DEFAULT_ATTRIBUTES

def get_context_patterns():
    return Path(__file__).resolve().parent / '_context_config.json'
    