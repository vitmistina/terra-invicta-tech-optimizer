from __future__ import annotations

import json
from dataclasses import asdict

import streamlit as st

from terra_invicta_tech_optimizer import GraphFilters, ListFilters, backlog_reorder

from ..data import get_models
from ..graphviz import build_graphviz
from ..state import apply_backlog_addition, remove_backlog_item, reset_filters
from ..storage import persist_backlog_storage
from .shared import (
    friendly_name,
    label_for_index,
    option_choices,
    parse_backlog_order,
    render_sortable_backlog_compact,
    render_validation,
)


def _persist_after_mutation() -> None:
    models = st.session_state.get("models")
    if not models:
        return
    graph_data = models.get("graph_data")
    if graph_data is None:
        return

    st.session_state.backlog_storage_dirty = True
    persist_backlog_storage(graph_data)


def render_filters(nodes) -> None:
    _, flat_list = get_models(nodes)
    filters: ListFilters = st.session_state.filters
    categories = list(flat_list.categories)

    st.subheader("Filters")
    st.caption("Focus the list and results on categories, completion state, or backlog.")

    selected_categories = st.multiselect(
        "Categories",
        options=categories,
        default=sorted(filters.categories) if filters.categories else [],
    )

    include_completed = st.checkbox("Show completed", value=filters.include_completed)
    include_incomplete = st.checkbox(
        "Show incomplete", value=filters.include_incomplete
    )
    backlog_only = st.checkbox("Backlog only", value=filters.backlog_only)

    st.session_state.filters = ListFilters(
        categories=frozenset(selected_categories) if selected_categories else None,
        include_completed=include_completed,
        include_incomplete=include_incomplete,
        backlog_only=backlog_only,
    )

    cols = st.columns(2)
    with cols[0]:
        st.button("Reset filters", type="secondary", on_click=reset_filters, width="stretch")
    with cols[1]:
        filters = st.session_state.filters
        if (
            filters.categories
            or not filters.include_completed
            or not filters.include_incomplete
            or backlog_only
        ):
            st.info("Filters are active")
        else:
            st.caption("All nodes visible")


def render_backlog(nodes) -> None:
    st.subheader("Backlog")
    st.caption("Drag and drop to reorder. Use the list to add items.")

    _, flat_list = get_models(nodes)
    backlog = st.session_state.backlog_state

    if not backlog.order:
        st.caption("No backlog items yet.")
        return

    order_value = st.text_input(
        "Backlog order",
        value=json.dumps([str(idx) for idx in backlog.order]),
        key="backlog_order",
        label_visibility="collapsed",
    )
    st.markdown(
        "<style>input[aria-label='Backlog order'] { display: none; }</style>",
        unsafe_allow_html=True,
    )
    new_order = parse_backlog_order(order_value, backlog)
    if new_order is not None and new_order != backlog.order:
        st.session_state.backlog_state = backlog_reorder(backlog, new_order)
        backlog = st.session_state.backlog_state
        st.session_state.backlog_order = json.dumps([str(idx) for idx in backlog.order])
        _persist_after_mutation()

    render_sortable_backlog_compact(backlog, flat_list=flat_list)

    remove_map: dict[str, int] = {}
    for idx in backlog.order:
        remove_map[label_for_index(idx, flat_list=flat_list)] = idx

    selected_label = st.selectbox("Remove item", ["Select item"] + list(remove_map.keys()))
    node_to_remove = remove_map.get(selected_label)
    st.button(
        "Remove selected",
        on_click=remove_backlog_item,
        args=(node_to_remove,),
        width="stretch",
        type="secondary",
        disabled=node_to_remove is None,
    )


def render_completion(nodes) -> None:
    st.subheader("Completion state")
    st.caption("Mark items you've already finished to de-emphasize them.")
    _, flat_list = get_models(nodes)
    options = {
        label_for_index(idx, flat_list=flat_list): idx
        for idx in range(len(flat_list.rows))
    }
    default_labels = [
        label for label, idx in options.items() if idx in st.session_state.completed
    ]
    selected = st.multiselect(
        "Completed items", options=list(options.keys()), default=default_labels
    )
    st.session_state.completed = {options[name] for name in selected}


def render_graph(explorer, nodes) -> None:
    st.subheader("Graph explorer")
    st.caption(
        "Hover for details, select a node to focus prerequisites and dependents."
    )

    options = option_choices(nodes)
    option_labels = ["None"] + list(options.keys())
    default_label = next(
        (
            label
            for label, node_id in options.items()
            if node_id == st.session_state.selected
        ),
        "None",
    )
    selected_label = st.selectbox(
        "Focus node", option_labels, index=option_labels.index(default_label)
    )
    st.session_state.selected = options.get(selected_label)

    graph_data, _ = get_models(nodes)
    list_filters: ListFilters = st.session_state.filters
    graph_filters = GraphFilters(
        categories=set(list_filters.categories) if list_filters.categories else None,
        include_completed=list_filters.include_completed,
        include_incomplete=list_filters.include_incomplete,
        backlog_only=list_filters.backlog_only,
        hide_filtered=True,
    )

    graph_view = explorer.build_view(
        selected=st.session_state.selected,
        completed={graph_data.node_ids[idx] for idx in st.session_state.completed},
        backlog=[graph_data.node_ids[idx] for idx in st.session_state.backlog_state.order],
        filters=graph_filters,
    )

    graphviz_spec = build_graphviz(graph_view)
    st.graphviz_chart(graphviz_spec, width="stretch")

    with st.expander("Selection details", expanded=bool(st.session_state.selected)):
        if st.session_state.selected:
            node = nodes.get(st.session_state.selected)
            st.markdown(f"**{node.friendly_name}** ({node.node_type.value.title()})")
            st.write(f"Category: {node.category or 'Uncategorized'}")
            if node.prereqs:
                prereq_labels = ", ".join(
                    friendly_name(pid, nodes) for pid in node.prereqs
                )
                st.write(f"Prerequisites: {prereq_labels}")
            if node.metadata:
                st.json(node.metadata)

            graph_data, _ = get_models(nodes)
            node_index = graph_data.id_to_index.get(node.identifier)
            st.button(
                "Quick-add to backlog",
                on_click=apply_backlog_addition,
                args=(node_index,),
                type="primary",
            )
        else:
            st.caption("Select a node to see its dependencies and metadata.")

    with st.expander("Graph debug data"):
        st.write("Filters", asdict(st.session_state.filters))
        st.write("Selected", st.session_state.selected)
        st.write("Completed", list(st.session_state.completed))
        st.write("Backlog", list(st.session_state.backlog_state.order))


def render_validation_summary(result) -> None:
    render_validation(result)
