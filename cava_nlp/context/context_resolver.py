from collections import defaultdict
from typing import Dict, List, Tuple
from medspacy.context.context_modifier import ConTextModifier # type: ignore[import-untyped]
from medspacy.context.context_graph import ConTextGraph # type: ignore[import-untyped]
from typing import Protocol
from spacy.language import Language
from spacy.tokens import Doc, Span


def group_edges_by_target(edges: List[Tuple[Span, ConTextModifier]]) -> Dict[Span, List[ConTextModifier]]:
    grouped: dict[Span, List[ConTextModifier]] = defaultdict(list)
    for target, modifier in edges:
        grouped[target].append(modifier)
    return grouped


def modifier_distance(target: Span, modifier: ConTextModifier) -> int:
    """
    Distance in tokens between modifier and target.
    Lower = closer.
    """
    modifier_start, modifier_end = modifier.modifier_span
    if modifier_start <= target.start:
        return target.start - modifier_end
    elif modifier_start >= target.end:
        return modifier_start - target.end
    else:
        return 0  # overlapping (rare but strongest)
    
def resolve_closest_modifier(edges: List[Tuple[Span, ConTextModifier]]) -> List[Tuple[Span, ConTextModifier]]:
    grouped = group_edges_by_target(edges)
    resolved_edges: List[Tuple[Span, ConTextModifier]] = []

    for target, modifiers in grouped.items():
        best = min(
            modifiers,
            key=lambda m: modifier_distance(target, m)
        )
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
    doc._.context_graph = resolved_graph

    return doc
