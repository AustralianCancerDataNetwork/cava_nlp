from medspacy.section_detection import Sectionizer
from spacy.tokens import Doc
from spacy.language import Language
import dateutil.parser as dateparser
from typing import Union, Iterable, Optional, Dict, Any, Tuple, List, Literal, Set


@Language.factory('dated_sectionizer')
class DatedSectionizer(Sectionizer):
    # this is used to set start and end dates of section-level date references
    # for the purpose of date disambiguation of extracted tokens

    def __call__(self, doc: Doc) -> Doc:
        doc = super(DatedSectionizer, self).__call__(doc=doc)

        return doc

    def set_parent_sections(
        self, sections: List[Tuple[int, int, int]]
    ) -> List[Tuple[int, int, int, int]]:
        """
        Determine the legal parent-child section relationships from the list
        of in-order sections of a document and the possible parents of each
        section as specified during direction creation.

        Args:
            sections: a list of spacy match tuples found in the doc

        Returns:
            A list of tuples (match_id, start, end, parent_idx) where the first three indices are the same as the input
            and the added parent_idx represents the index in the list that corresponds to the parent section. Might be a
            smaller list than the input due to pruning with `parent_required`.
        """
        sections_final = []
        removed_sections = 0
        for i, (match_id, start, end) in enumerate(sections):
            name = self.__matcher.rule_map[self.nlp.vocab.strings[match_id]].category
            required = self._parent_required[name]
            i_a = i - removed_sections  # adjusted index for removed values
            if required and i_a == 0:
                removed_sections += 1
                continue
            elif i_a == 0 or name not in self._parent_sections.keys():
                sections_final.append((match_id, start, end, None))
            else:
                parents = self._parent_sections[name]
                identified_parent = None
                for parent in parents:
                    # go backwards through the section "tree" until you hit a root or the start of the list
                    candidate = self.__matcher.rule_map[
                        self.nlp.vocab.strings[sections_final[i_a - 1][0]]
                    ].category
                    candidates_parent_idx = sections_final[i_a - 1][3]
                    if candidates_parent_idx is not None:
                        candidates_parent = self.__matcher.rule_map[
                            self.nlp.vocab.strings[
                                sections_final[candidates_parent_idx][0]
                            ]
                        ].category
                    else:
                        candidates_parent = None
                    candidate_i = i_a - 1
                    while candidate:
                        if candidate == parent:
                            identified_parent = candidate_i
                            candidate = None
                        else:
                            # if you are at the end of the list... no parent
                            if candidate_i < 1:
                                candidate = None
                                continue
                            # if the current candidate has no parent... no parent exists
                            if not candidates_parent:
                                candidate = None
                                continue
                            # otherwise get the previous item in the list
                            temp = self.__matcher.rule_map[
                                self.nlp.vocab.strings[
                                    sections_final[candidate_i - 1][0]
                                ]
                            ].category
                            temp_parent_idx = sections_final[candidate_i - 1][3]
                            if temp_parent_idx is not None:
                                temp_parent = self.__matcher.rule_map[
                                    self.nlp.vocab.strings[
                                        sections_final[temp_parent_idx][0]
                                    ]
                                ].category
                            else:
                                temp_parent = None
                            # if the previous item is the parent of the current item
                            # OR if the previous item is a sibling of the current item
                            # continue to search
                            if (
                                temp == candidates_parent
                                or temp_parent == candidates_parent
                            ):
                                candidate = temp
                                candidates_parent = temp_parent
                                candidate_i -= 1
                            # otherwise, there is no further tree traversal
                            else:
                                candidate = None

                # if a parent is required, then add
                if identified_parent is not None or not required:
                    # if the parent is identified, add section
                    # if the parent is not required, add section
                    # if parent is not identified and required, do not add the section
                    sections_final.append((match_id, start, end, identified_parent))
                else:
                    removed_sections += 1
        return sections_final