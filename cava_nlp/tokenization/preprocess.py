def condense_char_runs(text, char):
    """
    Replace multiple consecutive occurrences of `char`
    with a single instance.
    """
    result = []
    last = None
    for c in text:
        if c == char:
            if last != char:
                result.append(c)
        else:
            result.append(c)
        last = c
    return "".join(result)


def whitespace_preprocess(text, chars):
    """
    Apply whitespace/linebreak condensing rules before tokenization.
    """
    for c in chars:
        text = condense_char_runs(text, c)
    return text
