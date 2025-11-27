"""
Description: rule-based smoking attributes extractor 

Author: Ivy C Valerie

Date: 2024-08-26

"""

from spacy.language import Language
from cava_nlp.value_extraction.value_extractor import ValueExtractor
from cava_nlp.value_extraction.label_matcher import get_widest_match


@Language.factory("cava_smoking_extractor")
def create_smoking_status(nlp, name):
    return SmokingExtractor(nlp.vocab)


class SmokingExtractor(ValueExtractor):
    def __init__(self, vocab, *args, **kwargs):
        super(SmokingExtractor, self).__init__(
            vocab=vocab,
            token_label="smoking_attribute",
            value_label="smoking_attribute_value",
            token_patterns=smoking_patterns,
            value_patterns=[smoking_qty],
            entity_label="SMOKING_ATTRIBUTES",
            exclusion_patterns=smoking_exclusion,
        )
        self.merge_ents = True

    def __call__(self, doc):
        """Merge overlapping widest matches"""

        spans, matches = self.get_token_spans(doc)
        sorted_matches = sorted(matches, key=lambda x: x[1])
        widest_matches = [
            m for m in sorted_matches if get_widest_match(m[1], m[2], sorted_matches)
        ]

        merged_matches = []
        for interval in widest_matches:
            if not merged_matches or merged_matches[-1][2] < interval[1]:
                merged_matches.append(interval)
            else:
                merged_matches[-1] = (
                    merged_matches[-1][0],
                    merged_matches[-1][1],
                    max(merged_matches[-1][2], interval[2]),
                )

        self.set_entity(doc, merged_matches)

        with doc.retokenize() as retokenizer:
            for m_id, start, end in merged_matches:
                span = doc[start:end]
                for tok in span:
                    tok._.set(self.token_label, True)
                if self.merge_ents:
                    retokenizer.merge(span)

        return doc


# update similar regex patterns at the same time
# for regex pattern, use \b to match word boundaries, otherwise it will match substring

# exclude clinical manifestation called "lead pipe rigidity"
smoking_exclusion = [[{"LOWER": {"IN": ["lead"]}}, {"LOWER": {"IN": ["pipe"]}}]]

# TODO: find more common names for tobacco products
smoking_keywords = [
    # preface for symmetry
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    r"\bcig(s|ar(ette)?(s)?)?\b",
                    r"\bsmok(e(d|r|s)?|in(g)?)\b",
                ]
            }
        },
        "OP": "?",
    },
    # core keywords
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    r"\bcig(s|ar(ette)?(s)?)?\b",
                    r"\bcrack\b",
                    r"\bnicotine\b",
                    r"\bpipe(s)?\b",
                    r"\bsmok(e(d|r|s)?|in(g)?)\b",
                    r"\btobacco\b",
                ]
            },
        }
    },
    # following status or numerics are included here to avoid span overlap
    {
        "LOWER": {
            "IN": [
                "abuse",
                "as",
                "for",
                "greater",
                "heavily",
                "history",
                "hx",
                "none",
                "that",
                "use",
            ]
        },
        "OP": "?",
    },
    {
        "LOWER": {"IN": ["approximately", "for", "in", "of", "than", "the", "was"]},
        "OP": "?",
    },
    {"LIKE_NUM": True, "OP": "?"},
    {"LOWER": {"IN": ["last", "the", "to"]}, "OP": "?"},
    {"LIKE_NUM": True, "OP": "?"},
    # time unit
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    r"\bd(ay(s)?)?\b",
                    r"\bm(on(th)?(s)?|th(s)?)?\b",
                    r"\bw(k(s)?|eek(s)?)?\b",
                    r"\by(o|r(s)?|ear(s)?)?\b",
                ]
            }
        },
        "OP": "?",
    },
    {"LOWER": {"IN": ["ago", "past"]}, "OP": "?"},
]

# find mentions of smoking cessation
smoking_tx = [
    {"LOWER": {"IN": ["smoking", "tobacco", "nicoderm", "nicotine", "nrt"]}},
    {"LOWER": {"IN": ["cessation", "patch"]}, "OP": "?"},
]

smoking_status = [
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    "-",
                    r"\bcontinue(d|s)?\b",
                    r"\bden(y|ies|ied)?\b",
                    r"\bdue\b",
                    r"\bex\b",
                    r"\bformer(ly)?\b",
                    r"\bha(s|ve)\b",
                    r"\bnegative\b",
                    r"\bno(n|t)\b",
                    r"\bpositive\b",
                    r"\bquit(s|ted|ting)?\b",
                    r"\bunable\b",
                ]
            }
        },
        "OP": "?",
    },
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    "-",
                    "\+",
                    r"\ba\b",
                    r"\ball\b",
                    r"\bany\b",
                    r"\bbeen\b",
                    r"\bchronic\b",
                    r"\bcurrent(ly)?\b",
                    r"\bden(y|ies|ied)?\b",
                    r"\bfor\b",
                    r"\bformer(ly)?\b",
                    r"\bheavy\b",
                    r"\blifelong\b",
                    r"\blongstanding\b",
                    r"\bnegative\b",
                    r"\bnever\b",
                    r"\bnil\b",
                    r"\bno(n|t)?\b",
                    r"\bocc(asion*)?\b",
                    r"\bon\b",
                    r"\bpast\b",
                    r"\bquit(s|ted|ting)?\b",
                    r"\bremote\b",
                    r"\bsignificant\b",
                    r"\bstay\b",
                    r"\bstill\b",
                    r"\bstop(s|ped)?\b",
                    r"\bto\b",
                    r"\bus(ed|ing)?\b",
                ]
            }
        },
        "OP": "?",
    },
]

smoking_qty = [
    # captures fraction and range of fraction
    {"LIKE_NUM": True, "OP": "?"},
    {"LOWER": {"IN": ["x", "-", "/"]}, "OP": "?"},
    {"LIKE_NUM": True, "OP": "?"},
    {"LOWER": {"IN": ["x", "-", "/"]}, "OP": "?"},
    {"LIKE_NUM": True, "OP": "?"},
    {"LOWER": {"IN": ["to", "x", "-", "/"]}, "OP": "?"},
    {"LIKE_NUM": True},
    {"LOWER": {"IN": ["x", "-", "+", "/"]}, "OP": "?"},
    # core keywords plus units
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    r"\bcig(s|ar(ette)?(s)?)?\b",
                    r"\bcrack\b",
                    r"\bnicotine\b",
                    r"\bp(ack(s)?|k(s)?|y(h)?)\b",
                    r"\bpipe(s)?\b",
                    r"\bpp[dwmy]\b",
                    r"\bpuff(s)?\b",
                    r"\btobacco\b",
                ]
            }
        }
    },
    {"LOWER": {"IN": ["of"]}, "OP": "?"},
    # tobacco products as unit extension, sourced from core keywords
    {
        "LOWER": {
            "REGEX": {
                "IN": [r"\bcig(s|ar(ette)?(s)?)?\b", r"\bcrack\b", r"\bpipe(s)?\b"]
            }
        },
        "OP": "?",
    },
    # "puff(s)?" need separate pattern/disambiguate with inhalated medication?
    {"LOWER": {"IN": ["a", "every", "per", "-", "/"]}, "OP": "?"},
    # time unit
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    r"\bd(ay(s)?)?\b",
                    r"\bm(on(th)?(s)?|th(s)?)?\b",
                    r"\bw(k(s)?|eek(s)?)?\b",
                    r"\by(o|r(s)?|ear(s)?)?\b",
                ]
            }
        },
        "OP": "?",
    },
    # duration
    {
        "LOWER": {
            "REGEX": {
                "IN": [r"\bfrom\b", r"\bquit(s|ted|ting)?\b", r"\btimes\b", r"\bx\b"]
            }
        },
        "OP": "?",
    },
    {"LOWER": {"IN": [">", "age", "approximately", "in"]}, "OP": "?"},
    {"LIKE_NUM": True, "OP": "?"},
    {
        "LOWER": {
            "REGEX": {
                "IN": [
                    r"\bd(ay(s)?)?\b",
                    r"\bm(on(th)?(s)?|th(s)?)?\b",
                    r"\bw(k(s)?|eek(s)?)?\b",
                    r"\bto\b",
                    r"\by(o|r(s)?|ear(s)?)?\b",
                ]
            }
        },
        "OP": "?",
    },
    {"LIKE_NUM": True, "OP": "?"},
]

smoking_patterns = [
    smoking_keywords,
    smoking_tx,
    smoking_qty,
    smoking_keywords + smoking_qty,
    smoking_status + smoking_keywords,
    smoking_status + smoking_keywords + smoking_qty,
]
