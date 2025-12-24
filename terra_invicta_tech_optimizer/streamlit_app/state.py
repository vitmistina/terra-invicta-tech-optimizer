from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from terra_invicta_tech_optimizer import (
    BacklogState,
    GraphData,
    ListFilters,
    backlog_add,
    backlog_remove,
    backlog_reorder,
)

from .storage import persist_backlog_storage


def _ensure_base_state() -> None:
    if "reload_token" not in st.session_state:
        st.session_state.reload_token = 0

    if "filters" not in st.session_state:
        st.session_state.filters = ListFilters.reset()

    if "selected" not in st.session_state:
        st.session_state.selected = None

    if "backlog_storage_dirty" not in st.session_state:
        st.session_state.backlog_storage_dirty = False


def _coerce_indices(value, *, graph_data: GraphData) -> list[int]:
    if value is None:
        return []
    if isinstance(value, (set, frozenset, tuple, list)):
        items = list(value)
    else:
        items = [value]

    indices: list[int] = []
    for item in items:
        if isinstance(item, int):
            if 0 <= item < graph_data.size:
                indices.append(item)
            continue
        node_id = str(item)
        idx = graph_data.id_to_index.get(node_id)
        if idx is not None:
            indices.append(idx)
    return indices


def ensure_state(nodes, *, graph_data: GraphData) -> None:
    _ensure_base_state()

    if st.session_state.selected not in nodes:
        st.session_state.selected = None

    if "backlog_state" not in st.session_state:
        legacy = st.session_state.get("backlog")
        legacy_indices = _coerce_indices(legacy, graph_data=graph_data)
        order = tuple(dict.fromkeys(legacy_indices))
        st.session_state.backlog_state = BacklogState(
            order=order, members=frozenset(order)
        )
    else:
        backlog_state: BacklogState = st.session_state.backlog_state
        order = tuple(idx for idx in backlog_state.order if 0 <= idx < graph_data.size)
        st.session_state.backlog_state = BacklogState(
            order=order, members=frozenset(order)
        )

    if "completed" not in st.session_state:
        legacy = st.session_state.get("completed")
        st.session_state.completed = set(_coerce_indices(legacy, graph_data=graph_data))
    else:
        st.session_state.completed = {
            idx for idx in st.session_state.completed if 0 <= idx < graph_data.size
        }


def reset_filters() -> None:
    st.session_state.filters = ListFilters.reset()


def _persist_after_mutation() -> None:
    models = st.session_state.get("models")
    if not models:
        return
    graph_data: GraphData | None = models.get("graph_data")
    if graph_data is None:
        return

    st.session_state.backlog_storage_dirty = True
    persist_backlog_storage(graph_data)


def apply_backlog_addition(node_index: int | None) -> None:
    if node_index is None:
        return
    st.session_state.backlog_state = backlog_add(
        st.session_state.backlog_state, node_index
    )
    _persist_after_mutation()


def apply_backlog_additions(node_indices: Iterable[int]) -> None:
    if not node_indices:
        return
    backlog_state: BacklogState = st.session_state.backlog_state
    for node_index in node_indices:
        if node_index is None:
            continue
        backlog_state = backlog_add(backlog_state, node_index)
    st.session_state.backlog_state = backlog_state
    _persist_after_mutation()


def remove_backlog_item(node_index: int | None) -> None:
    if node_index is None:
        return
    st.session_state.backlog_state = backlog_remove(
        st.session_state.backlog_state, node_index
    )
    _persist_after_mutation()


def apply_backlog_reorder(new_order: Iterable[int]) -> None:
    st.session_state.backlog_state = backlog_reorder(
        st.session_state.backlog_state, new_order
    )
    _persist_after_mutation()
