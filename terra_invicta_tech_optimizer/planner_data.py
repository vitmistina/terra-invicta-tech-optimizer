from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .input_loader import Node, NodeType


def _parse_cost(metadata: Mapping[str, Any]) -> int | None:
    raw_cost = metadata.get("researchCost")
    if raw_cost is None:
        return None
    try:
        cost = int(raw_cost)
    except (TypeError, ValueError):
        return None
    if cost < 0:
        return None
    return cost


@dataclass(frozen=True, slots=True)
class GraphData:
    node_ids: tuple[str, ...]
    id_to_index: Mapping[str, int]
    node_type: tuple[NodeType, ...]
    category: tuple[str | None, ...]
    friendly_name: tuple[str, ...]
    prereqs: tuple[tuple[int, ...], ...]
    dependents: tuple[tuple[int, ...], ...]

    @property
    def size(self) -> int:
        return len(self.node_ids)


def build_graph_data(nodes: Mapping[str, Node]) -> GraphData:
    node_ids = tuple(sorted(nodes.keys(), key=lambda value: (value.casefold(), value)))
    id_to_index = {node_id: idx for idx, node_id in enumerate(node_ids)}

    node_type: list[NodeType] = []
    category: list[str | None] = []
    friendly_name: list[str] = []
    prereqs: list[tuple[int, ...]] = []

    dependents_work: list[list[int]] = [[] for _ in range(len(node_ids))]

    for node_id in node_ids:
        node = nodes[node_id]
        node_type.append(node.node_type)
        category.append(node.category)
        friendly_name.append(node.friendly_name)

        prereq_indices: list[int] = []
        for prereq_id in node.prereqs:
            idx = id_to_index.get(prereq_id)
            if idx is None:
                continue
            prereq_indices.append(idx)
            dependents_work[idx].append(id_to_index[node_id])
        prereqs.append(tuple(prereq_indices))

    dependents: list[tuple[int, ...]] = [tuple(items) for items in dependents_work]

    return GraphData(
        node_ids=node_ids,
        id_to_index=MappingProxyType(id_to_index),
        node_type=tuple(node_type),
        category=tuple(category),
        friendly_name=tuple(friendly_name),
        prereqs=tuple(prereqs),
        dependents=tuple(dependents),
    )


@dataclass(frozen=True, slots=True)
class FlatNodeRow:
    index: int
    node_id: str
    friendly_name: str
    friendly_name_casefold: str
    node_type: NodeType
    category: str | None
    cost: int | None


@dataclass(frozen=True, slots=True)
class FlatNodeList:
    rows: tuple[FlatNodeRow, ...]
    categories: tuple[str, ...]
    category_to_indices: Mapping[str, tuple[int, ...]]
    category_sorted_by_name: Mapping[str, tuple[int, ...]]
    category_sorted_by_cost_desc: Mapping[str, tuple[int, ...]]


def build_flat_node_list(graph: GraphData, nodes: Mapping[str, Node]) -> FlatNodeList:
    rows: list[FlatNodeRow] = []
    category_buckets: dict[str, list[int]] = {}

    for index, node_id in enumerate(graph.node_ids):
        node = nodes[node_id]
        row = FlatNodeRow(
            index=index,
            node_id=node_id,
            friendly_name=node.friendly_name,
            friendly_name_casefold=node.friendly_name.casefold(),
            node_type=node.node_type,
            category=node.category,
            cost=_parse_cost(node.metadata),
        )
        rows.append(row)
        category_label = node.category or "Uncategorized"
        category_buckets.setdefault(category_label, []).append(index)

    categories = tuple(
        sorted(category_buckets.keys(), key=lambda value: value.casefold())
    )

    category_to_indices: dict[str, tuple[int, ...]] = {
        category: tuple(indices) for category, indices in category_buckets.items()
    }

    def sort_by_name(indices: Iterable[int]) -> tuple[int, ...]:
        return tuple(sorted(indices, key=lambda idx: rows[idx].friendly_name_casefold))

    def sort_by_cost_desc(indices: Iterable[int]) -> tuple[int, ...]:
        def key(idx: int):
            cost = rows[idx].cost
            missing = cost is None
            return (missing, -(cost or 0), rows[idx].friendly_name_casefold)

        return tuple(sorted(indices, key=key))

    category_sorted_by_name = {
        category: sort_by_name(indices)
        for category, indices in category_to_indices.items()
    }
    category_sorted_by_cost_desc = {
        category: sort_by_cost_desc(indices)
        for category, indices in category_to_indices.items()
    }

    return FlatNodeList(
        rows=tuple(rows),
        categories=categories,
        category_to_indices=MappingProxyType(category_to_indices),
        category_sorted_by_name=MappingProxyType(category_sorted_by_name),
        category_sorted_by_cost_desc=MappingProxyType(category_sorted_by_cost_desc),
    )


@dataclass(frozen=True, slots=True)
class ListFilters:
    categories: frozenset[str] | None = None
    include_completed: bool = True
    include_incomplete: bool = True
    backlog_only: bool = False
    search_query: str | None = None

    @classmethod
    def reset(cls) -> "ListFilters":
        return cls()


@dataclass(frozen=True, slots=True)
class FlatListView:
    visible_by_category: Mapping[str, tuple[int, ...]]

    @property
    def visible_indices(self) -> tuple[int, ...]:
        indices: list[int] = []
        for items in self.visible_by_category.values():
            indices.extend(items)
        return tuple(indices)


def build_flat_list_view(
    flat_list: FlatNodeList,
    *,
    filters: ListFilters,
    completed: set[int],
    backlog_members: set[int],
    sort_mode: str,
) -> FlatListView:
    if sort_mode.startswith("Tech cost"):
        sorted_map = flat_list.category_sorted_by_cost_desc
    else:
        sorted_map = flat_list.category_sorted_by_name

    allowed_categories = filters.categories
    include_completed = filters.include_completed
    include_incomplete = filters.include_incomplete
    backlog_only = filters.backlog_only
    search_query = filters.search_query

    # Normalize search query for case-insensitive substring matching
    search_normalized = search_query.strip().casefold() if search_query else None

    visible_by_category: dict[str, tuple[int, ...]] = {}

    for category in flat_list.categories:
        if allowed_categories is not None and category not in allowed_categories:
            continue

        ordered_indices = sorted_map.get(category, ())
        visible = []
        for idx in ordered_indices:
            is_completed = idx in completed
            in_backlog = idx in backlog_members

            passes_completion = (is_completed and include_completed) or (
                not is_completed and include_incomplete
            )
            if not passes_completion:
                continue
            if backlog_only and not in_backlog:
                continue

            # Apply search filter if query is present
            if search_normalized:
                row = flat_list.rows[idx]
                if search_normalized not in row.friendly_name_casefold:
                    continue

            visible.append(idx)

        if visible:
            visible_by_category[category] = tuple(visible)

    return FlatListView(visible_by_category=MappingProxyType(visible_by_category))


@dataclass(frozen=True, slots=True)
class BacklogState:
    order: tuple[int, ...] = ()
    members: frozenset[int] = frozenset()


def explode_backlog(
    graph: GraphData, backlog_order: Iterable[int], completed: set[int]
) -> tuple[int, ...]:
    seen: dict[int, bool] = {}
    ordered: list[int] = []

    def visit(index: int) -> None:
        if index in seen:
            return
        researched = index in completed
        seen[index] = researched
        if not researched:
            for prereq in graph.prereqs[index]:
                visit(prereq)
        ordered.append(index)

    for index in backlog_order:
        if 0 <= index < graph.size:
            visit(index)

    return tuple(ordered)


def backlog_add(backlog: BacklogState, index: int) -> BacklogState:
    if index in backlog.members:
        return backlog
    order = backlog.order + (index,)
    return BacklogState(order=order, members=backlog.members | {index})


def backlog_remove(backlog: BacklogState, index: int) -> BacklogState:
    if index not in backlog.members:
        return backlog
    order = tuple(item for item in backlog.order if item != index)
    return BacklogState(order=order, members=frozenset(order))


def backlog_reorder(backlog: BacklogState, new_order: Iterable[int]) -> BacklogState:
    seen: set[int] = set()
    cleaned: list[int] = []

    for item in new_order:
        if item in backlog.members and item not in seen:
            cleaned.append(item)
            seen.add(item)

    for item in backlog.order:
        if item not in seen:
            cleaned.append(item)
            seen.add(item)

    order = tuple(cleaned)
    return BacklogState(order=order, members=frozenset(order))
