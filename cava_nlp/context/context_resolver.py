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

    # --- sentence penalty ---
    target_sent = target.sent
    modifier_sent = target.doc[modifier_start].sent

    if target_sent is modifier_sent:
        sent_penalty = 0
    else:
        sent_penalty = sentence_penalty

    return token_dist + sent_penalty
    
def resolve_closest_modifier(edges: List[Tuple[Span, ConTextModifier]]) -> List[Tuple[Span, ConTextModifier]]:
    grouped = group_edges_by_target(edges)
    resolved_edges: List[Tuple[Span, ConTextModifier]] = []

    for target, modifiers in grouped.items():

        best: ConTextModifier | None = None
        best_dist = REJECT_DISTANCE

        for modifier in modifiers:
            dist = modifier_distance(target, modifier)
            if dist < best_dist:
                best_dist = dist
                best = modifier

        if best is not None:
            resolved_edges.append((target, best))

    return resolved_edges


class ContextResolver(Protocol):
    def resolve(self, graph: ConTextGraph) -> ConTextGraph: ...

class ClosestModifierResolver:

    def resolve(self, graph: ConTextGraph) -> ConTextGraph:
        resolved_edges = resolve_closest_modifier(graph.edges) # type: ignore[import-untyped]
        graph.edges = resolved_edges
        return graph


@Language.component("resolve_closest_context")
def resolve_closest_context(doc: Doc) -> Doc:
    graph = doc._.context_graph
    if graph is None or not graph.edges:
        return doc

    resolver = ClosestModifierResolver()

    # mutate in place OR replace graph
    resolved_graph = resolver.resolve(graph)
    # reset context state
    targets = {target for target, _ in resolved_graph.edges}
    for target in targets:
        clear_context_attrs(target)
    # reapply from resolved graph
    apply_context_from_graph(resolved_graph)
    doc._.context_graph = resolved_graph

    return doc
