from medspacy.section_detection import Sectionizer, SectionRule
from spacy.tokens import Span
from ._sectionizer_config import sections, line_break, sectionizer_attrs

def get_sent_start_toks(literal):
    literals = literal.replace('/',' / ').replace('&', ' & ').replace('-', ' - ').split()
    return [{"LOWER":{"FUZZY2": t}, "IS_SENT_START": i==0} if len(t) >= 6 else {"LOWER":t, "IS_SENT_START": i==0} for i, t in enumerate(literals)]

def get_toks(literal):
    literals = literal.replace('/',' / ').replace('&', ' & ').replace('-', ' - ').split()
    return [{"LOWER":{"FUZZY2": t}} if len(t) >= 6 else {"LOWER":t} for t in literals]

def register_additional_attributes():
    for attr in ['section_historical', 'section_current', 'section_family','section_hypothetical', 'is_current']:
        try:
            Span.set_extension(attr, default=False)
        except ValueError:
            ... # already set

def get_sectionizer_attrs():
    register_additional_attributes()
    return sectionizer_attrs

def get_sectionizer_patterns():
    patterns = [x for y in [[SectionRule(category=k, literal=vv, pattern=get_sent_start_toks(vv) + [{"_": {"time": True}, "OP":"?"}, {"TEXT": {"IN": [":","-", ";"]}}]) for vv in v] for k, v in sections.items()] for x in y]
    patterns += [x for y in [[SectionRule(category=k, literal=vv, pattern=[{"TEXT": "-", "IS_SENT_START": True}] +  get_toks(vv)) for vv in v] for k, v in sections.items()] for x in y]
    patterns += [x for y in [[SectionRule(category=k, literal=vv, pattern=get_sent_start_toks(vv) + [{"_": {"time": True}, "OP":"?"}] + line_break) for vv in v] for k, v in sections.items()] for x in y]
    patterns += [x for y in [[SectionRule(category=k, literal=vv, pattern=line_break + get_toks(vv) + [{"_": {"time": True}, "OP":"?"}, {"TEXT": {"IN": [":","-", ";"]}}]) for vv in v] for k, v in sections.items()] for x in y]
    patterns += [x for y in [[SectionRule(category=k, literal=vv, pattern=line_break + [{"TEXT": "-"}] + get_toks(vv)) for vv in v] for k, v in sections.items()] for x in y]
    patterns += [x for y in [[SectionRule(category=k, literal=vv, pattern=line_break + get_toks(vv) + [{"_": {"time": True}, "OP":"?"}] + line_break) for vv in v] for k, v in sections.items()] for x in y]
    patterns += [SectionRule(category='dated_section', literal='dated_section', pattern=line_break + [{"_": {"date":True}}]), 
                 SectionRule(category='undated_section', literal='undated_section', pattern=[{"LOWER": {"IN":["\n\n", "\n \n"]}}])]
    return patterns