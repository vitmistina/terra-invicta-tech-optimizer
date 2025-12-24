from __future__ import annotations

import json
import re
from html import escape as html_escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from st_keyup import st_keyup

from main import (
    STATIC_DIR,
    CATEGORY_ICON_MAP,
    BacklogState,
    FlatNodeList,
    ListFilters,
    apply_backlog_addition,
    backlog_reorder,
    build_flat_list_view,
    ensure_state,
    get_models,
    load_inputs,
    persist_backlog_storage,
    hydrate_backlog_from_storage,
    remove_backlog_item,
    render_validation,
    validate_graph,
)


st.set_page_config(
    page_title="Terra Invicta Technology Planner - Start Here",
    layout="wide",
    page_icon="🛸",
)

# Global CSS for sticky header and sidebar
st.markdown(
    """
    <style>
    /* Reduce default padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Hide Streamlit's default header */
    header[data-testid="stHeader"] {
        display: none;
    }
    
    /* Sticky left sidebar - target horizontal block children */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
        position: sticky;
        top: 1rem;
        align-self: flex-start;
        height: fit-content;
        z-index: 100;
    }
    
    /* Hide the search hidden input container completely */
    .search-hidden-container {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _label_for_index(index: int, *, flat_list: FlatNodeList) -> str:
    row = flat_list.rows[index]
    kind = row.node_type.value.title()
    category = row.category or "Uncategorized"
    return f"{row.friendly_name} | {kind} | {category} [{row.node_id}]"


def _format_cost(cost: int | None) -> str:
    return f"{cost:,}" if cost is not None else "N/A"


def _category_icon_path(category: str | None) -> Path | None:
    if not category:
        return None
    key = re.sub(r"[^a-z0-9]", "", str(category).casefold())
    filename = CATEGORY_ICON_MAP.get(key)
    if not filename:
        return None
    path = STATIC_DIR / filename
    return path if path.exists() else None


def _parse_backlog_order(value: str, backlog: BacklogState) -> tuple[int, ...] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None

    allowed = backlog.members
    seen: set[int] = set()
    cleaned: list[int] = []

    for item in parsed:
        try:
            idx = int(item)
        except (TypeError, ValueError):
            continue
        if idx in allowed and idx not in seen:
            cleaned.append(idx)
            seen.add(idx)

    for idx in backlog.order:
        if idx not in seen:
            cleaned.append(idx)
            seen.add(idx)

    return tuple(cleaned)


def _render_sortable_backlog(backlog: BacklogState, *, flat_list: FlatNodeList) -> None:
    """Custom HTML/JS drag-drop backlog with theme-safe styling."""
    items = []
    for idx in backlog.order:
        if idx < 0 or idx >= len(flat_list.rows):
            continue
        row = flat_list.rows[idx]
        label = f"{row.friendly_name} ({row.node_type.value.title()})"
        safe_label = html_escape(label)
        safe_id = html_escape(str(idx))
        items.append(
            f'<li class="backlog-item" draggable="true" data-id="{safe_id}">{safe_label}</li>'
        )

    list_html = "\n".join(items)
    html = f"""
    <div class="backlog-root">
      <ul class="backlog-list">
        {list_html}
      </ul>
    </div>
    <script>
    const list = document.querySelector(".backlog-list");
    if (list) {{
      const parentDoc = window.parent.document;
      let dragItem = null;

      const updateInput = () => {{
        const order = Array.from(list.querySelectorAll(".backlog-item")).map((el) => el.dataset.id);
        const input = parentDoc.querySelector("input[aria-label='Backlog order']");
        if (!input) return;
        input.value = JSON.stringify(order);
        input.dispatchEvent(new Event("input", {{ bubbles: true }}));
      }};

      list.addEventListener("dragstart", (event) => {{
        dragItem = event.target.closest(".backlog-item");
        event.dataTransfer.effectAllowed = "move";
      }});

      list.addEventListener("dragover", (event) => {{
        event.preventDefault();
        const target = event.target.closest(".backlog-item");
        if (!target || target === dragItem) return;
        const rect = target.getBoundingClientRect();
        const next = (event.clientY - rect.top) > (rect.height / 2);
        list.insertBefore(dragItem, next ? target.nextSibling : target);
      }});

      list.addEventListener("drop", () => updateInput());
      list.addEventListener("dragend", () => updateInput());
    }}
    </script>
    <style>
    .backlog-root {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .backlog-list {{
      list-style: none;
      padding-left: 0;
      margin: 0;
    }}
    .backlog-item {{
      padding: 10px 12px;
      margin-bottom: 8px;
      background: white;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      cursor: grab;
      user-select: none;
      color: #1f2937;
      font-size: 0.9rem;
      transition: box-shadow 0.15s, border-color 0.15s;
    }}
    .backlog-item:hover {{
      border-color: #9ca3af;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .backlog-item:active {{
      cursor: grabbing;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    @media (prefers-color-scheme: dark) {{
      .backlog-item {{
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
      }}
      .backlog-item:hover {{
        border-color: #6b7280;
      }}
    }}
    </style>
    """
    height = min(250, 46 * max(1, len(items)) + 10)
    components.html(html, height=height, scrolling=True)


def _update_search_filter(value: str) -> None:
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

    # Get the current search value (from filters or empty string)
    current_value = current_filters.search_query or ""

    # Render search box with debounce for better performance
    search_value = st_keyup(
        "Search by friendly name...",
        value=current_value,
        debounce=300,  # 300ms debounce for smooth typing
        placeholder="🔍 Search will happen 300 ms after you stop typing",
        key="search_input_widget",
    )

    # Update filter if search value changed
    if search_value != current_value:
        _update_search_filter(search_value)


def render_header():
    """Render header row with title."""
    st.title("🛸 Terra Invicta Technology Planner")
    st.caption(
        "Build your backlog, search technologies, and calculate the optimal path."
    )


def render_filters_container(nodes):
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

        # Update filters but preserve search_query
        st.session_state.filters = ListFilters(
            categories=frozenset(selected_categories) if selected_categories else None,
            include_completed=include_completed,
            include_incomplete=include_incomplete,
            backlog_only=backlog_only,
            search_query=filters.search_query,
        )


def render_backlog_container(nodes):
    """Render backlog panel in a bordered container."""
    _, flat_list = get_models(nodes)
    backlog: BacklogState = st.session_state.backlog_state

    with st.container(border=True):
        st.markdown("##### 📋 BACKLOG")

        if not backlog.order:
            st.info("No items yet. Add from the list →", icon="💡")
        else:
            st.caption(f"{len(backlog.order)} items • Drag to reorder")

            # Hidden input for drag-drop order updates
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
            new_order = _parse_backlog_order(order_value, backlog)
            if new_order is not None and new_order != backlog.order:
                st.session_state.backlog_state = backlog_reorder(backlog, new_order)
                backlog = st.session_state.backlog_state
                st.session_state.backlog_order = json.dumps(
                    [str(idx) for idx in backlog.order]
                )
                _persist_after_mutation()

            _render_sortable_backlog(backlog, flat_list=flat_list)

            # Remove item section
            remove_map: dict[str, int] = {}
            for idx in backlog.order:
                remove_map[_label_for_index(idx, flat_list=flat_list)] = idx

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

        # Calculate button
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


def render_technology_list(nodes):
    """Render the technology list."""
    filters: ListFilters = st.session_state.filters

    # Search status indicator
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
        # Map short labels to full sort mode strings
        sort_mode = (
            "Tech cost (desc)" if sort_mode == "Cost ↓" else "Friendly name (A-Z)"
        )

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

    # Count visible items
    total_visible = sum(len(v) for v in view.visible_by_category.values())
    st.caption(f"Showing {total_visible} items")

    # Apply theme-safe list styling
    st.markdown(
        """
        <style>
        .tech-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 26px;
          height: 26px;
          border-radius: 6px;
          font-weight: 700;
          font-size: 0.8rem;
        }
        .tech-badge.tech {
          background: #dbeafe;
          border: 1px solid #3b82f6;
          color: #1e40af;
        }
        .tech-badge.project {
          background: #dcfce7;
          border: 1px solid #16a34a;
          color: #166534;
        }
        .tech-name { font-weight: 600; font-size: 0.95rem; }
        .tech-cost {
          text-align: right;
          font-family: "Consolas", monospace;
          font-size: 0.85rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for category in flat_list.categories:
        visible_indices = view.visible_by_category.get(category)
        if not visible_indices:
            continue

        with st.expander(f"**{category}** ({len(visible_indices)})", expanded=True):
            for idx in visible_indices:
                row = flat_list.rows[idx]
                cost_text = _format_cost(row.cost)

                status_parts = []
                if idx in backlog_state.members:
                    status_parts.append("📋")
                if idx in completed:
                    status_parts.append("✓")
                status_text = " ".join(status_parts)

                in_backlog = idx in backlog_state.members
                badge_text = "T" if row.node_type.value == "tech" else "P"
                badge_kind = "tech" if row.node_type.value == "tech" else "project"

                row_cols = st.columns([0.06, 0.5, 0.15, 0.08, 0.1])

                icon_path = _category_icon_path(row.category)
                if icon_path:
                    row_cols[0].image(str(icon_path), width=24)
                else:
                    row_cols[0].markdown(
                        f"<span class='tech-badge {badge_kind}'>{badge_text}</span>",
                        unsafe_allow_html=True,
                    )

                row_cols[1].markdown(
                    f"<div class='tech-name'>{html_escape(row.friendly_name)}</div>",
                    unsafe_allow_html=True,
                )
                row_cols[2].markdown(
                    f"<div class='tech-cost'>{cost_text}</div>",
                    unsafe_allow_html=True,
                )
                row_cols[3].write(status_text)
                row_cols[4].button(
                    "✅" if in_backlog else "➕",
                    key=f"list-{row.node_id}",
                    on_click=apply_backlog_addition,
                    args=(idx,),
                    disabled=in_backlog,
                )


def _sync_search_from_query_params() -> None:
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


def main():
    if "reload_token" not in st.session_state:
        st.session_state.reload_token = 0

    load_report = load_inputs(st.session_state.get("reload_token", 0))

    if load_report.errors:
        st.error("Encountered errors while loading inputs:")
        for error in load_report.errors:
            st.write(f"- {error}")
        st.stop()

    graph_data, _ = get_models(load_report.nodes)
    ensure_state(load_report.nodes, graph_data=graph_data)

    decoded = hydrate_backlog_from_storage(graph_data)
    dropped = st.session_state.get("backlog_storage_dropped")
    if decoded and decoded.dropped:
        st.info(
            "Some stored backlog items were ignored because they are missing in this dataset: "
            + ", ".join(decoded.dropped),
            icon="ℹ️",
        )
    elif dropped:
        st.info(
            "Some stored backlog items were ignored because they are missing in this dataset: "
            + ", ".join(dropped),
            icon="ℹ️",
        )

    write_error = st.session_state.get("backlog_storage_write_error")
    if write_error:
        st.warning(
            "Backlog changes may not persist in this browser (storage unavailable).",
            icon="⚠️",
        )

    # Sync search from URL query params (must be after ensure_state)
    _sync_search_from_query_params()

    validation_result = validate_graph(load_report.nodes)
    if validation_result.has_errors:
        render_validation(validation_result)
        st.stop()

    # Header
    render_header()
    st.divider()

    # Two-column layout
    left_col, right_col = st.columns([1, 2], gap="large")

    with left_col:
        # Search box (sticky with the sidebar)
        render_search_box()

        # Filters container (separate)
        render_filters_container(load_report.nodes)

        # Backlog container (separate)
        render_backlog_container(load_report.nodes)

    with right_col:
        render_technology_list(load_report.nodes)


if __name__ == "__main__":
    main()
