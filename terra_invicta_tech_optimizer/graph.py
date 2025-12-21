from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Set, Tuple

from .input_loader import Node, NodeType


CATEGORY_COLORS: Dict[str | None, str] = {
    "Energy": "#ffd166",
    "Social": "#ffafcc",
    "Space": "#6ec6ff",
    "Xeno": "#c77dff",
    None: "#d3d3d3",
}

NODE_TYPE_SHAPES: Dict[NodeType, str] = {
    NodeType.TECH: "dot",
    NodeType.PROJECT: "square",
}


@dataclass
class GraphNodeStyle:
    color: str
    shape: str


@dataclass
class GraphNodeView:
    identifier: str
    label: str
    node_type: NodeType
    category: str | None
    style: GraphNodeStyle
    prereqs: list[str]
    metadata: dict[str, Any]
    is_completed: bool = False
    in_backlog: bool = False
    is_selected: bool = False
    is_prerequisite: bool = False
    is_dependent: bool = False
    is_dimmed: bool = False
    is_hidden: bool = False


@dataclass
class GraphEdgeView:
    source: str
    target: str
    is_highlighted: bool = False
    is_dimmed: bool = False
    is_hidden: bool = False


@dataclass
class GraphFilters:
    categories: set[str] | None = None
    include_completed: bool = True
    include_incomplete: bool = True
    backlog_only: bool = False
    hide_filtered: bool = False

    @classmethod
    def reset(cls) -> "GraphFilters":
        return cls()


@dataclass
class GraphView:
    nodes: list[GraphNodeView] = field(default_factory=list)
    edges: list[GraphEdgeView] = field(default_factory=list)
    selected: str | None = None
    filters: GraphFilters = field(default_factory=GraphFilters)


class GraphExplorer:
    """Prepare graph data for visualization and filtering."""

    def __init__(self, nodes: Dict[str, Node]):
        self.nodes = nodes
        self._dependents_map = self._build_dependents_map(nodes)
        self._view_cache: Dict[Tuple[Any, ...], GraphView] = {}

    def build_view(
        self,
        *,
        selected: str | None = None,
        completed: Iterable[str] | None = None,
        backlog: Iterable[str] | None = None,
        filters: GraphFilters | None = None,
    ) -> GraphView:
        completed_set = set(completed or [])
        backlog_set = set(backlog or [])
        filters = filters or GraphFilters()

        cache_key = self._cache_key(selected, completed_set, backlog, filters)
        if cache_key in self._view_cache:
            return self._view_cache[cache_key]

        prerequisite_highlight = self._walk_prerequisites(selected) if selected else set()
        dependent_highlight = self._walk_dependents(selected) if selected else set()

        node_views = [
            self._build_node_view(
                node,
                selected=selected,
                completed_set=completed_set,
                backlog_set=backlog_set,
                filters=filters,
                prerequisite_highlight=prerequisite_highlight,
                dependent_highlight=dependent_highlight,
            )
            for node in self.nodes.values()
        ]

        node_visibility = {node.identifier: not node.is_hidden for node in node_views}
        edge_views = self._build_edges(node_visibility, selected, prerequisite_highlight, dependent_highlight, filters)

        view = GraphView(nodes=node_views, edges=edge_views, selected=selected, filters=filters)
        self._view_cache[cache_key] = view
        return view

    def _build_node_view(
        self,
        node: Node,
        *,
        selected: str | None,
        completed_set: Set[str],
        backlog_set: Set[str],
        filters: GraphFilters,
        prerequisite_highlight: Set[str],
        dependent_highlight: Set[str],
    ) -> GraphNodeView:
        is_completed = node.identifier in completed_set
        in_backlog = node.identifier in backlog_set

        passes_category = not filters.categories or (node.category in filters.categories)
        passes_completion = (is_completed and filters.include_completed) or (
            not is_completed and filters.include_incomplete
        )
        passes_backlog = (not filters.backlog_only) or in_backlog
        is_visible = passes_category and passes_completion and passes_backlog

        is_hidden = filters.hide_filtered and not is_visible
        is_dimmed = (not filters.hide_filtered) and not is_visible

        return GraphNodeView(
            identifier=node.identifier,
            label=node.friendly_name,
            node_type=node.node_type,
            category=node.category,
            style=self._style_for(node),
            prereqs=list(node.prereqs),
            metadata=dict(node.metadata),
            is_completed=is_completed,
            in_backlog=in_backlog,
            is_selected=node.identifier == selected,
            is_prerequisite=node.identifier in prerequisite_highlight,
            is_dependent=node.identifier in dependent_highlight,
            is_dimmed=is_dimmed,
            is_hidden=is_hidden,
        )

    def _build_edges(
        self,
        node_visibility: Dict[str, bool],
        selected: str | None,
        prerequisite_highlight: Set[str],
        dependent_highlight: Set[str],
        filters: GraphFilters,
    ) -> list[GraphEdgeView]:
        edges: list[GraphEdgeView] = []

        for target, node in self.nodes.items():
            for prereq in node.prereqs:
                if prereq not in self.nodes:
                    continue

                is_hidden = filters.hide_filtered and (not node_visibility.get(target, True) or not node_visibility.get(prereq, True))
                is_dimmed = (not filters.hide_filtered) and (
                    not node_visibility.get(target, True) or not node_visibility.get(prereq, True)
                )
                is_highlighted = False

                if selected:
                    if target == selected and prereq in prerequisite_highlight:
                        is_highlighted = True
                    if prereq == selected and target in dependent_highlight:
                        is_highlighted = True
                    if target in prerequisite_highlight and prereq in prerequisite_highlight:
                        is_highlighted = True
                    if target in dependent_highlight and prereq in dependent_highlight:
                        is_highlighted = True

                edges.append(
                    GraphEdgeView(
                        source=prereq,
                        target=target,
                        is_highlighted=is_highlighted,
                        is_dimmed=is_dimmed,
                        is_hidden=is_hidden,
                    )
                )

        return edges

    def _walk_prerequisites(self, selected: str | None) -> Set[str]:
        if not selected or selected not in self.nodes:
            return set()

        visited: Set[str] = set()

        def dfs(node_id: str) -> None:
            node = self.nodes.get(node_id)
            if not node:
                return
            for prereq in node.prereqs:
                if prereq in visited:
                    continue
                visited.add(prereq)
                dfs(prereq)

        dfs(selected)
        return visited

    def _walk_dependents(self, selected: str | None) -> Set[str]:
        if not selected or selected not in self.nodes:
            return set()

        visited: Set[str] = set()

        def dfs(node_id: str) -> None:
            for dependent in self._dependents_map.get(node_id, []):
                if dependent in visited:
                    continue
                visited.add(dependent)
                dfs(dependent)

        dfs(selected)
        return visited

    def _style_for(self, node: Node) -> GraphNodeStyle:
        base_color = CATEGORY_COLORS.get(node.category, CATEGORY_COLORS[None])
        shape = NODE_TYPE_SHAPES.get(node.node_type, "dot")
        return GraphNodeStyle(color=base_color, shape=shape)

    @staticmethod
    def _build_dependents_map(nodes: Dict[str, Node]) -> Dict[str, List[str]]:
        dependents: Dict[str, List[str]] = {}
        for node in nodes.values():
            for prereq in node.prereqs:
                dependents.setdefault(prereq, []).append(node.identifier)
        return dependents

    def _cache_key(
        self,
        selected: str | None,
        completed: Set[str],
        backlog: Iterable[str] | None,
        filters: GraphFilters,
    ) -> Tuple[Any, ...]:
        backlog_order = tuple(backlog or [])
        filters_key = (
            tuple(sorted(filters.categories)) if filters.categories else None,
            filters.include_completed,
            filters.include_incomplete,
            filters.backlog_only,
            filters.hide_filtered,
        )
        return (selected, tuple(sorted(completed)), backlog_order, filters_key)

