from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

from .analysis import is_meaningful_term


def build_symbol_graph(dreams: list[dict[str, Any]], *, max_nodes: int = 12, max_edges: int = 24) -> dict[str, list[dict[str, Any]]]:
    node_counts: Counter[str] = Counter()
    edge_counts: Counter[tuple[str, str]] = Counter()

    for dream in dreams:
        analysis = dream.get("analysis") or {}
        terms = []
        for value in analysis.get("symbols") or []:
            text = str(value).strip()
            if is_meaningful_term(text):
                terms.append(text)
        unique_terms = sorted(set(terms), key=str.casefold)
        node_counts.update(unique_terms)
        edge_counts.update(tuple(pair) for pair in combinations(unique_terms, 2))

    nodes = [
        {"id": name, "label": name, "count": count}
        for name, count in sorted(node_counts.items(), key=lambda item: (-item[1], item[0].casefold()))[:max_nodes]
    ]
    node_ids = {node["id"] for node in nodes}
    edges = [
        {"source": source, "target": target, "weight": weight}
        for (source, target), weight in sorted(edge_counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1]))
        if source in node_ids and target in node_ids
    ][:max_edges]
    return {"nodes": nodes, "edges": edges}
