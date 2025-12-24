from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from st_keyup import st_keyup

from terra_invicta_tech_optimizer import BacklogState, ListFilters, backlog_reorder, build_flat_list_view

from ..data import get_models
from ..state import apply_backlog_additions, remove_backlog_item
from ..storage import persist_backlog_storage
from .shared import (
    category_icon_path,
    format_cost,
    label_for_index,
    parse_backlog_order,
    render_sortable_backlog_panel,
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


def update_search_filter(value: str) -> None:
    """Update filters and query params from the search box input."""
    filters: ListFilters = st.session_state.filters
    normalized = value.strip()

    st.session_state.filters = ListFilters(
        categories=filters.categories,
        include_completed=filters.include_completed,
        include_incomplete=filters.include_incomplete,
        backlog_only=filters.backlog_only,
        search_query=normalized if normalized else None,
    )

    if normalized:
        st.query_params["search"] = normalized
    elif "search" in st.query_params:
        del st.query_params["search"]


def render_search_box() -> None:
    """Render a search box using st_keyup for live filtering with debounce."""
    current_filters: ListFilters = st.session_state.filters
    current_value = current_filters.search_query or ""

    search_value = st_keyup(
        "Search by friendly name...",
        value=current_value,
        debounce=300,
        placeholder="🔍 Search will happen 300 ms after you stop typing",
        key="search_input_widget",
    )

    if search_value != current_value:
        update_search_filter(search_value)


def render_header() -> None:
    """Render header row with title."""
    st.title("🛸 Terra Invicta Technology Planner")
    st.caption("Build your backlog, search technologies, and calculate the optimal path.")


def render_filters_container(nodes) -> None:
    """Render filter controls in a bordered container."""
    _, flat_list = get_models(nodes)
    filters: ListFilters = st.session_state.filters
    categories = list(flat_list.categories)

    with st.container(border=True):
        st.markdown("##### ⚙️ FILTERS")

        selected_categories = st.multiselect(
            "Categories",
            options=categories,
            default=sorted(filters.categories) if filters.categories else [],
            key="filter_categories",
        )

        col1, col2 = st.columns(2)
        with col1:
            include_completed = st.checkbox(
                "Completed", value=filters.include_completed, key="filter_completed"
            )
        with col2:
            include_incomplete = st.checkbox(
                "Incomplete", value=filters.include_incomplete, key="filter_incomplete"
            )

        backlog_only = st.checkbox(
            "Backlog only", value=filters.backlog_only, key="filter_backlog_only"
        )

        st.session_state.filters = ListFilters(
            categories=frozenset(selected_categories) if selected_categories else None,
            include_completed=include_completed,
            include_incomplete=include_incomplete,
            backlog_only=backlog_only,
            search_query=filters.search_query,
        )


def render_backlog_container(nodes) -> None:
    """Render backlog panel in a bordered container."""
    _, flat_list = get_models(nodes)
    backlog: BacklogState = st.session_state.backlog_state

    with st.container(border=True):
        st.markdown("##### 📋 BACKLOG")

        if not backlog.order:
            st.info("No items yet. Add from the list →", icon="💡")
        else:
            st.caption(f"{len(backlog.order)} items • Drag to reorder")

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
                st.session_state.backlog_order = json.dumps(
                    [str(idx) for idx in backlog.order]
                )
                _persist_after_mutation()

            render_sortable_backlog_panel(backlog, flat_list=flat_list)

            remove_map: dict[str, int] = {}
            for idx in backlog.order:
                remove_map[label_for_index(idx, flat_list=flat_list)] = idx

            col1, col2 = st.columns([4, 1])
            with col1:
                selected_label = st.selectbox(
                    "Remove item",
                    ["Select to remove..."] + list(remove_map.keys()),
                    key="backlog_remove_select",
                    label_visibility="collapsed",
                )
            with col2:
                node_to_remove = remove_map.get(selected_label)
                st.button(
                    "🗑️",
                    on_click=remove_backlog_item,
                    args=(node_to_remove,),
                    disabled=node_to_remove is None,
                    key="backlog_remove_btn",
                    help="Remove selected item",
                )

        st.divider()

        if st.button(
            "🚀 Calculate optimal path",
            type="primary",
            use_container_width=True,
            key="calc_path_btn",
        ):
            st.session_state.simulation_result = None
            st.session_state.simulation_config = None
            st.session_state.calculation_requested = True
            st.switch_page("pages/Results.py")


def render_technology_list(nodes) -> None:
    """Render the technology list."""
    filters: ListFilters = st.session_state.filters

    if filters.search_query:
        st.success(f"🔍 Filtered by: **{filters.search_query}**", icon="✅")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("##### TECHNOLOGY LIST")
    with col2:
        sort_mode = st.radio(
            "Sort",
            ("A-Z", "Cost ↓"),
            horizontal=True,
            key="sort_mode_radio",
            label_visibility="collapsed",
            index=1,
        )
        sort_mode = "Tech cost (desc)" if sort_mode == "Cost ↓" else "Friendly name (A-Z)"

    _, flat_list = get_models(nodes)
    completed: set[int] = set(st.session_state.completed)
    backlog_state: BacklogState = st.session_state.backlog_state

    view = build_flat_list_view(
        flat_list,
        filters=filters,
        completed=completed,
        backlog_members=set(backlog_state.members),
        sort_mode=sort_mode,
    )

    if not view.visible_by_category:
        st.warning("No items match the current filters or search.")
        return

    total_visible = sum(len(v) for v in view.visible_by_category.values())
    st.caption(f"Showing {total_visible} items")

    for category in flat_list.categories:
        visible_indices = view.visible_by_category.get(category)
        if not visible_indices:
            continue

        with st.expander(f"{category} ({len(visible_indices)})", expanded=True):
            header_cols = st.columns([0.06, 0.94])
            icon_path = category_icon_path(category)
            if icon_path:
                header_cols[0].image(str(icon_path), width=24)
            header_cols[1].markdown(f"**{category}**")

            rows = []
            for idx in visible_indices:
                row = flat_list.rows[idx]
                status_parts = []
                if idx in backlog_state.members:
                    status_parts.append("📋")
                if idx in completed:
                    status_parts.append("✓")
                status_text = " ".join(status_parts)

                rows.append(
                    {
                        "Select": False,
                        "Friendly Name": row.friendly_name,
                        "Type": row.node_type.value.title(),
                        "Cost": format_cost(row.cost),
                        "Status": status_text,
                        "_index": idx,
                    }
                )

            table = pd.DataFrame(rows).set_index("_index")
            editor_key = f"category-editor-{category}"
            edited_table = st.data_editor(
                table,
                key=editor_key,
                hide_index=True,
                disabled=("Friendly Name", "Type", "Cost", "Status"),
                column_config={
                    "Select": st.column_config.CheckboxColumn(required=False),
                    "Friendly Name": st.column_config.TextColumn(width="large"),
                    "Type": st.column_config.TextColumn(width="small"),
                    "Cost": st.column_config.TextColumn(width="small"),
                    "Status": st.column_config.TextColumn(width="small"),
                },
                width="stretch",
            )

            selected_indices = [
                int(idx)
                for idx, row in edited_table.iterrows()
                if row.get("Select")
            ]
            if st.button(
                "Add selected to backlog",
                key=f"category-add-{category}",
                disabled=not selected_indices,
                width="stretch",
            ):
                apply_backlog_additions(selected_indices)
                cleared = edited_table.copy()
                cleared["Select"] = False
                st.session_state[editor_key] = cleared


def sync_search_from_query_params() -> None:
    """Sync search query param to filters state. Must be called after ensure_state."""
    param_search = st.query_params.get("search", "")
    if isinstance(param_search, list):
        param_search = param_search[-1] if param_search else ""

    current_filters: ListFilters = st.session_state.filters
    current_search = current_filters.search_query or ""

    if param_search != current_search:
        st.session_state.filters = ListFilters(
            categories=current_filters.categories,
            include_completed=current_filters.include_completed,
            include_incomplete=current_filters.include_incomplete,
            backlog_only=current_filters.backlog_only,
            search_query=param_search if param_search else None,
        )
