from typing import Iterable

def condense_char_runs(text: str, char: str) -> str:
    """
    Replace multiple consecutive occurrences of `char`
    with a single instance.
    """
    result: list[str] = []
    last = None
    for c in text:
        if c == char:
            if last != char:
                result.append(c)
        else:
            result.append(c)
        last = c
    return "".join(result)


def whitespace_preprocess(text: str, chars: Iterable[str]) -> str:
    """
    Apply whitespace/linebreak condensing rules before tokenization.
    We preserve breaks but avoids false emphasis - in practice, this 
    is especially important for date attribution and sectionising.

    This works by stabilising sentence, date and section boundary heuristics.
    """
    for c in chars:
        text = condense_char_runs(text, c)
    return text
