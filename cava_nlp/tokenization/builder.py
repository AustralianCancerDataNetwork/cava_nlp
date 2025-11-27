import re
import spacy
from spacy.lang.en import English


def build_cava_prefixes():
    """
    Build custom prefixes for brutal clinical splitting.
    """
    base = list(English.Defaults.prefixes) # type: ignore

    extra = [
        "@", r"\?", "~", "<", ">", ";", r"\^",
        r"\(", r"\)", r"\|", "-", "=", ":",
        r"\+\+\+", r"\+\+", r"\+", r"\.", r"\d+",
        "/", "SGA", "PGSGA"
    ]

    # Remove '+'-related prefixes from default
    base = [p for p in base if r'\+' not in p] # type: ignore

    return extra + base


def build_cava_suffixes():

    base = list(English.Defaults.suffixes) # type: ignore

    extra = [
        "@", "~", "<", ">", ";", r"\(", r"\)", r"\|",
        "=", ":", "/", "-", ",",
        r"\+\+\+", r"\+\+", r"\+", "--"
    ]

    base = [s for s in base if "GB" not in s] # type: ignore

    return extra + base


def build_cava_infixes():

    base = list(English.Defaults.infixes) # type: ignore

    extra = [
        r"\/",  r"-", r"\*", r"\^", r"(?<!\d)\.(?!\d)", # r"\.", - now it still uses a period infix but only outside numbers
        r"&", "@", "<", ">", ";", ":",
        r"\?", r",", r"\(", r"\)", r"\|",
        "~", r"=", r"\+\+\+", r"\+\+", r"\+",
        # alpha-digit and digit-alpha boundaries
        r"(?<=[A-Za-z])(?=\d)",
        r"(?<=\d)(?=[A-Za-z])",
    ]

    # Add hyphens from char classes (e.g., unicode hyphens)
    extra += list(spacy.lang.char_classes.LIST_HYPHENS) # type: ignore

    return extra + base

