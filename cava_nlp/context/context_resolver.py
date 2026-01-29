from collections import defaultdict
from typing import Dict, List, Tuple
from medspacy.context.context_modifier import ConTextModifier # type: ignore[import-untyped]
from medspacy.context.context_graph import ConTextGraph # type: ignore[import-untyped]
from typing import Protocol
from spacy.language import Language
from spacy.tokens import Doc, Span
from ..context.registry import LOCAL_ATTRIBUTES

REJECT_DISTANCE: int = 1_000_000

CONTEXT_ATTRS: set[str] = {
    attr_name
    for attr_map in LOCAL_ATTRIBUTES.values()
    for attr_name in attr_map.keys()
}

ATTACHED_SIGNS = {"-", "+"}

def is_attached_sign(
    target: Span,
    modifier: ConTextModifier,
) -> bool:
    """
    Return True if modifier is a +/- sign is orthographically attached 
    across a contiguous, no-whitespace token chain to the target span, 
    allowing slash-chains like HER2/BRCA-.
    """
    m_start, _ = modifier.modifier_span
    # ensure NO SPACE between target and sign
    for tok in target.doc[target.start : m_start]:
        # Any whitespace breaks attachment
        if tok.whitespace_:
            return False
    return True


def enclosing_span(
    index: int,
    spans: list[tuple[int, int]],
) -> tuple[int, int] | None:
    """
    Return the (start, end) span that contains `index`, if any.

    Structural locality beats linear proximity
    
    i.e. If a target lives inside a structural unit (parenthetical 
    or list item), then modifiers outside that unit should be considered 
    *further away* even if token-distance is small.
    """
    for start, end in spans:
        if start <= index < end:
            return (start, end)
    return None

def structural_penalty(
    target: Span,
    modifier: ConTextModifier,
    *,
    parentheticals: list[tuple[int, int]],
    list_items: list[tuple[int, int]],
    multiplier: int = 3,
) -> int:
    """
    Penalise modifiers that cross structural boundaries
    (parentheticals or list items).
    """
    t_start = target.start
    m_start, _ = modifier.modifier_span

    # --- parenthetical containment ---
    t_paren = enclosing_span(t_start, parentheticals)
    if t_paren is not None:
        m_paren = enclosing_span(m_start, parentheticals)
        if m_paren != t_paren:
            return multiplier

    # --- list item containment ---
    t_list = enclosing_span(t_start, list_items)
    if t_list is not None:
        m_list = enclosing_span(m_start, list_items)
        if m_list != t_list:
            return multiplier

    return 1

def clear_context_attrs(span: Span) -> None:
    """
    We reset all context attributes on the span to False, because 
    the context graph that has been resolved will be the source of truth,
    and we don't know if any attributes were set elsewhere.
    """
    for attr in CONTEXT_ATTRS:
        if Span.has_extension(attr):
            # Use False, not None — context attrs are booleans
            setattr(span._, attr, False)

def apply_context_from_graph(graph: ConTextGraph) -> None:
    """
    Reapply context attributes to target spans based on resolved graph edges.
    """
    for target, modifier in graph.edges:
        # modifier.category is e.g. "POSITIVE"
        cat = modifier.category
        props = LOCAL_ATTRIBUTES[cat]
        for attr, value in props.items():
            if Span.has_extension(attr):
                setattr(target._, attr, value)

def group_edges_by_target(edges: List[Tuple[Span, ConTextModifier]]) -> Dict[Span, List[ConTextModifier]]:
    grouped: dict[Span, List[ConTextModifier]] = defaultdict(list)
    for target, modifier in edges:
        grouped[target].append(modifier)
    return grouped

def modifier_distance(
    target: Span,
    modifier: ConTextModifier,
    *,
    sentence_penalty: int = 50,
    parentheticals: list[tuple[int, int]] | None = None,
    list_items: list[tuple[int, int]] | None = None,
    structural_multiplier: int = 3,
) -> int:
    modifier_start, modifier_end = modifier.modifier_span

    # --- base token distance ---
    if modifier_start <= target.start:
        token_dist = target.start - modifier_end
    elif modifier_start >= target.end:
        token_dist = modifier_start - target.end
    else:
        # reject modifiers internal to target span
        return REJECT_DISTANCE

    tok = target.doc[modifier_start:modifier_end]
    # special case: attached +/- sign
    if tok.text in ATTACHED_SIGNS:
        is_attached = is_attached_sign(target, modifier)
        if is_attached and not tok[0]._.is_bullet:
            return 0
        return REJECT_DISTANCE
    # --- sentence penalty ---
    target_sent = target.sent
    modifier_sent = target.doc[modifier_start].sent

    if target_sent is modifier_sent:
        sent_penalty = 0
    else:
        sent_penalty = sentence_penalty

    if parentheticals is not None or list_items is not None:
        factor = structural_penalty(
            target,
            modifier,
            parentheticals=parentheticals or [],
            list_items=list_items or [],
            multiplier=structural_multiplier,
        )
        token_dist *= factor

    return token_dist + sent_penalty
    
def resolve_closest_modifier(
        edges: List[Tuple[Span, ConTextModifier]],
        *,
        parentheticals: list[tuple[int, int]] | None = None,
        list_items: list[tuple[int, int]] | None = None,
) -> List[Tuple[Span, ConTextModifier]]:
    
    grouped = group_edges_by_target(edges)
    resolved_edges: List[Tuple[Span, ConTextModifier]] = []

    for target, modifiers in grouped.items():

        best: ConTextModifier | None = None
        best_dist = REJECT_DISTANCE

        for modifier in modifiers:
            dist = modifier_distance(
                target,
                modifier,
                parentheticals=parentheticals,
                list_items=list_items,
            )
            if dist < best_dist:
                best_dist = dist
                best = modifier

        if best is not None:
            resolved_edges.append((target, best))

    return resolved_edges

class ContextResolver(Protocol):
    # other graph-based resolvers can implement this interface
    def resolve(self, graph: ConTextGraph, *, parentheticals: list[tuple[int, int]] | None = None, list_items: list[tuple[int, int]] | None = None) -> ConTextGraph: ...

class ClosestModifierResolver:

    def __init__(self, nlp: Language):
        self.nlp = nlp
        
    def resolve(
            self, 
            graph: ConTextGraph, 
            *, 
            parentheticals: list[tuple[int, int]] | None = None, 
            list_items: list[tuple[int, int]] | None = None
    ) -> ConTextGraph:
        resolved_edges = resolve_closest_modifier(graph.edges, parentheticals=parentheticals, list_items=list_items) # type: ignore[import-untyped]
        graph.edges = resolved_edges
        return graph
    
    def __call__(self, doc: Doc) -> Doc:
        graph = doc._.context_graph
        if graph is None or not graph.edges:
            return doc

        parentheticals = getattr(doc._, "parentheticals", [])
        list_items = getattr(doc._, "list_items", [])
        resolved_graph = self.resolve(graph, parentheticals=parentheticals, list_items=list_items)
        targets = {target for target, _ in resolved_graph.edges}
        # reset context state
        for target in targets:
            clear_context_attrs(target)
        # reapply from resolved graph
        apply_context_from_graph(resolved_graph)
        doc._.context_graph = resolved_graph
        return doc


@Language.factory("resolve_closest_context")
def create_context_resolver(nlp, name):
    return ClosestModifierResolver(nlp)