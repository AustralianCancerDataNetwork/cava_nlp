from medspacy.section_detection import Sectionizer, SectionRule
from spacy.tokens import Doc
from spacy.language import Language
import dateutil.parser as dateparser
from typing import Union, Iterable, Optional, Dict, Any, Tuple, List, Literal, Set

class DatedRule(SectionRule):

    def __init__(self, literal: str, 
                 category: str, 
                 pattern: Optional[Union[List[Dict[str, str]], str]] = None, 
                 top_level: bool = False):
        super(DatedRule, self).__init__(literal=literal, 
                                        category=category, 
                                        pattern=pattern)
        self.top_level = top_level



@Language.factory('dated_sectionizer')
class DatedSectionizer(Sectionizer):
    # this is used to set start and end dates of section-level date references
    # for the purpose of date disambiguation of extracted tokens

    def __init__(self, nlp, name, rules, span_attrs):
        super(DatedSectionizer, self).__init__(nlp=nlp, name=name, rules=rules, span_attrs=span_attrs)
        self._top_level = []
        try:
            Doc.set_extension('date_mapper', default={})
        except ValueError:
            pass

    def __call__(self, doc: Doc) -> Doc:
        doc = super(DatedSectionizer, self).__call__(doc=doc)
        doc._.date_mapper = {}
        for i, section in enumerate(doc._.sections):
            if section.category == 'date_time_section':
                try:
                    doc._.date_mapper[i] = dateparser.parse(doc[section.title_start:section.title_end].text, dayfirst=True)
                except:
                    print(doc[section.title_start:section.title_end])
            elif section.parent:
                doc._.date_mapper[i] = dateparser.parse(doc[section.parent.title_start:section.parent.title_end].text, dayfirst=True)
            else:
                doc._.date_mapper[i] = None
        return doc

    def add(self, rules):

        if isinstance(rules, DatedRule):
            rules = [rules]
        for rule in rules:
            if not isinstance(rule, DatedRule):
                raise TypeError("For dated sectionizer, rules must be type DatedRule, not", type(rule))

        super(DatedSectionizer, self).add(rules)

        for rule in rules:
            name = rule.category
            top_level = rule.top_level
            if top_level and name not in self._top_level:
                self._top_level.append(name)
                self._parent_sections[name] = []


    def set_parent_sections(
        self, sections: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int, int, int]]:
        """
        We have overridden this functionality for the purpose of cascading top-level dates to their children sections.

        In this setting, this takes the form of emails that autopopulate the notes and often contain quite useful data, but which 
        are challenging to disambiguate.

        In the below example, we expect event [a] to have the date exam_date, [b] to have the header email date from the first (most 
        recent) email and [c] to have the header email date from the second, older, email.

        We do this by setting sections to have the property 'top_level'. If they are top level, they will subsume all other sections
        until such time as they hit another top_level section.

        After section detection has been run, we then create a mapping between section and date. For the child sections, if they have 
        an explicit date, that one is populated, else revert to parent date.

        ----dd/mm/yyyy h:nn:ss----
        [email body]
        [exam_date]: exam results [a]
        blah blah blah

        o/e: some other info we might want to extract [b]...

        ----dd/mm/yyyy h:nn:ss----
        [second email body]

        results: [c]
        """
        sections_final = []
        i_a = 0
        for i, (match_id, start, end) in enumerate(sections):
            if (i == 0 and start != 0):
                i_a = 1 
            name = self._Sectionizer__matcher.rule_map[self.nlp.vocab.strings[match_id]].category
            top = name in self._top_level
            if i == 0 or top:
                candidate_children = sections[i+1:]
                for child_id, child_start, child_end in candidate_children:
                    child_name = self._Sectionizer__matcher.rule_map[self.nlp.vocab.strings[child_id]].category
                    if not child_name in self._top_level:
                        sections_final.append((child_id, child_start, child_end, i + i_a))
                    else:
                        sections_final.append((match_id, start, end, None))
                        break
        return sorted(sections_final, key=lambda x: x[1])