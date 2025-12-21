from __future__ import annotations

import json
import re
from dataclasses import asdict
from html import escape as html_escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from terra_invicta_tech_optimizer import (
    GraphExplorer,
    GraphFilters,
    GraphValidator,
    InputLoader,
)


BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "inputs"
STATIC_DIR = BASE_DIR / "static"

CATEGORY_ICON_MAP = {
    "energy": "30px-Tech_energy_icon.png",
    "informationscience": "30px-Tech_info_icon.png",
    "lifescience": "30px-Tech_life_icon.png",
    "materials": "30px-Tech_material_icon.png",
    "militaryscience": "30px-Tech_military_icon.png",
    "socialscience": "30px-Tech_social_icon.png",
    "spacescience": "30px-Tech_space_icon.png",
    "xenology": "30px-Tech_xeno_icon.png",
    "info": "30px-Tech_info_icon.png",
    "life": "30px-Tech_life_icon.png",
    "military": "30px-Tech_military_icon.png",
    "social": "30px-Tech_social_icon.png",
    "space": "30px-Tech_space_icon.png",
    "xeno": "30px-Tech_xeno_icon.png",
}


def _load_inputs(reload_token: int):
    loader = InputLoader(INPUT_DIR)
    return loader.load()


@st.cache_data(show_spinner=False)
def load_inputs(reload_token: int):
    return _load_inputs(reload_token)


def validate_graph(nodes):
    return GraphValidator(nodes).validate()


def ensure_state(nodes):
    if "reload_token" not in st.session_state:
        st.session_state.reload_token = 0

    if "filters" not in st.session_state:
        st.session_state.filters = GraphFilters()

    node_ids = set(nodes.keys())

    if "backlog" not in st.session_state:
        st.session_state.backlog = []
    else:
        st.session_state.backlog = [node for node in st.session_state.backlog if node in node_ids]

    if "completed" not in st.session_state:
        st.session_state.completed = set()
    else:
        st.session_state.completed = {node for node in st.session_state.completed if node in node_ids}

    if "selected" not in st.session_state:
        st.session_state.selected = None
    elif st.session_state.selected not in node_ids:
        st.session_state.selected = None


def get_explorer(nodes):
    reload_token = st.session_state.get("reload_token", 0)
    explorer_state = st.session_state.get("explorer")

    if explorer_state and explorer_state.get("token") == reload_token:
        return explorer_state["instance"]

    explorer = GraphExplorer(nodes)
    st.session_state.explorer = {"instance": explorer, "token": reload_token}
    return explorer


def reset_filters():
    st.session_state.filters = GraphFilters.reset()


def apply_backlog_addition(node_id: str | None):
    if not node_id:
        return
    backlog: list[str] = st.session_state.backlog
    if node_id not in backlog:
        backlog.append(node_id)


def remove_backlog_item(node_id: str | None):
    if not node_id:
        return
    st.session_state.backlog = [node for node in st.session_state.backlog if node != node_id]


def build_graphviz(view):
    lines = ["digraph G {"]
    lines.append("rankdir=LR;")
    lines.append("graph [pad=0.2];")
    lines.append("node [style=filled];")

    for node in view.nodes:
        if node.is_hidden:
            continue

        base_color = node.style.color
        fillcolor = _dim_color(base_color, 0.25) if node.is_dimmed else base_color
        stroke = "#ff6b6b" if node.is_selected else "#4b5563"
        penwidth = "3" if node.is_selected or node.in_backlog else "1.5"
        peripheries = "2" if node.in_backlog else "1"
        tooltip = _build_tooltip(node)

        badge = []
        if node.is_completed:
            badge.append("✓ Completed")
        if node.is_prerequisite:
            badge.append("Prereq")
        if node.is_dependent:
            badge.append("Dependent")
        if node.in_backlog:
            badge.append("Backlog")
        badge_text = " | ".join(badge)

        label_lines = [f"<B>{node.label}</B>"]
        if node.category:
            label_lines.append(node.category)
        if badge_text:
            label_lines.append(f"<FONT POINT-SIZE='10'>{badge_text}</FONT>")

        label = "<" + "<BR/>".join(label_lines) + ">"
        shape = "box" if node.node_type.value == "project" else "ellipse"

        lines.append(
            f'"{node.identifier}" [label={label} shape={shape} fillcolor="{fillcolor}" color="{stroke}" penwidth={penwidth} peripheries={peripheries} tooltip="{tooltip}" fontname="Inter" fontsize=12];'
        )

    for edge in view.edges:
        if edge.is_hidden:
            continue
        color = "#94a3b8"
        if edge.is_highlighted:
            color = "#fb7185"
        elif edge.is_dimmed:
            color = "#cbd5e1"
        lines.append(f'"{edge.source}" -> "{edge.target}" [color="{color}" penwidth=1.4 arrowsize=0.8];')

    lines.append("}")
    return "\n".join(lines)


def _dim_color(hex_color: str, factor: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_tooltip(node):
    details = [node.label]
    if node.category:
        details.append(f"Category: {node.category}")
    if node.prereqs:
        details.append("Prereqs: " + ", ".join(node.prereqs))
    for key, value in node.metadata.items():
        details.append(f"{key}: {value}")
    return " | ".join(details)


def _friendly_name(node_id: str, nodes) -> str:
    node = nodes.get(node_id)
    return node.friendly_name if node else node_id


def _option_choices(nodes):
    entries: dict[str, str] = {}
    for node_id, node in nodes.items():
        label_parts = [node.friendly_name]
        label_parts.append(node.node_type.value.title())
        if node.category:
            label_parts.append(node.category)
        label = " | ".join(label_parts) + f" [{node_id}]"
        entries[label] = node_id
    return dict(sorted(entries.items(), key=lambda item: item[0].lower()))


def _node_cost(node) -> int | None:
    raw_cost = node.metadata.get("researchCost")
    if raw_cost is None:
        return None
    try:
        cost = int(raw_cost)
    except (TypeError, ValueError):
        return None
    if cost < 0:
        return None
    return cost


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


def _matches_filters(node, completed: set[str], backlog: set[str], filters: GraphFilters) -> bool:
    is_completed = node.identifier in completed
    in_backlog = node.identifier in backlog
    passes_category = not filters.categories or (node.category in filters.categories)
    passes_completion = (is_completed and filters.include_completed) or (
        not is_completed and filters.include_incomplete
    )
    passes_backlog = (not filters.backlog_only) or in_backlog
    return passes_category and passes_completion and passes_backlog


def _sort_nodes_for_list(nodes, mode: str):
    if mode.startswith("Tech cost"):
        def _cost_key(node):
            cost = _node_cost(node)
            missing = cost is None
            return (missing, -(cost or 0), node.friendly_name.lower())

        return sorted(nodes, key=_cost_key)
    return sorted(nodes, key=lambda node: node.friendly_name.lower())


def _parse_backlog_order(value: str, backlog: list[str]) -> list[str] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    seen: set[str] = set()
    cleaned: list[str] = []
    allowed = set(backlog)
    for item in parsed:
        node_id = str(item)
        if node_id in allowed and node_id not in seen:
            cleaned.append(node_id)
            seen.add(node_id)
    for node_id in backlog:
        if node_id not in seen:
            cleaned.append(node_id)
            seen.add(node_id)
    return cleaned


def _render_sortable_backlog(backlog: list[str], nodes) -> None:
    # Custom HTML/JS updates a hidden Streamlit text input with the reordered IDs.
    items = []
    for node_id in backlog:
        node = nodes.get(node_id)
        if not node:
            continue
        label = f"{node.friendly_name} ({node.node_type.value.title()})"
        safe_label = html_escape(label)
        safe_id = html_escape(node_id)
        items.append(f'<li class="backlog-item" draggable="true" data-id="{safe_id}">{safe_label}</li>')

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
        if (!input) {{
          return;
        }}
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
        if (!target || target === dragItem) {{
          return;
        }}
        const rect = target.getBoundingClientRect();
        const next = (event.clientY - rect.top) > (rect.height / 2);
        list.insertBefore(dragItem, next ? target.nextSibling : target);
      }});

      list.addEventListener("drop", () => {{
        updateInput();
      }});

      list.addEventListener("dragend", () => {{
        updateInput();
      }});
    }}
    </script>
    <style>
    .backlog-root {{
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }}
    .backlog-list {{
      list-style: none;
      padding-left: 0;
      margin: 0;
    }}
    .backlog-item {{
      padding: 8px 10px;
      margin-bottom: 6px;
      background: #f8fafc;
      border: 1px solid #cbd5f5;
      border-radius: 6px;
      cursor: grab;
      user-select: none;
    }}
    .backlog-item:active {{
      cursor: grabbing;
    }}
    </style>
    """
    height = min(360, 38 * max(1, len(items)) + 20)
    components.html(html, height=height, scrolling=True)


def render_validation(result):
    if result.has_errors:
        with st.container(border=True):
            st.error("Validation failed. Resolve blocking issues to continue planning.")
            for issue in result.errors:
                st.write(f"**{issue.message}**: {', '.join(issue.nodes)}")
    else:
        with st.container(border=True):
            st.success("Graph validated. Ready for planning.")
            if result.warnings:
                st.warning("Warnings detected:")
                for warning in result.warnings:
                    st.write(f"**{warning.message}**: {', '.join(warning.nodes)}")


def render_filters(nodes):
    filters: GraphFilters = st.session_state.filters
    categories = sorted({node.category for node in nodes.values() if node.category})

    st.subheader("Filters")
    st.caption("Focus the list and results on categories, completion state, or backlog.")

    selected_categories = st.multiselect(
        "Categories",
        options=categories,
        default=sorted(filters.categories) if filters.categories else [],
    )

    include_completed = st.checkbox("Show completed", value=filters.include_completed)
    include_incomplete = st.checkbox("Show incomplete", value=filters.include_incomplete)
    backlog_only = st.checkbox("Backlog only", value=filters.backlog_only)
    hide_filtered = st.checkbox("Hide filtered nodes", value=filters.hide_filtered)

    filters.categories = set(selected_categories) if selected_categories else None
    filters.include_completed = include_completed
    filters.include_incomplete = include_incomplete
    filters.backlog_only = backlog_only
    filters.hide_filtered = hide_filtered

    cols = st.columns(2)
    with cols[0]:
        st.button("Reset filters", type="secondary", on_click=reset_filters, width="stretch")
    with cols[1]:
        if filters.categories or not filters.include_completed or not filters.include_incomplete or backlog_only or hide_filtered:
            st.info("Filters are active")
        else:
            st.caption("All nodes visible")


def render_node_list(nodes):
    st.subheader("Technology and project list")
    st.caption("Click an item to add it to the backlog.")
    st.markdown(
        """
        <style>
        .tech-list-scope {
          --tech-text: #e2e8f0;
          --tech-muted: #94a3b8;
          --tech-border: #334155;
          --tech-pill: #1f2937;
          --tech-tech-bg: #1e3a8a;
          --tech-tech-border: #1d4ed8;
          --tech-tech-text: #dbeafe;
          --tech-proj-bg: #14532d;
          --tech-proj-border: #16a34a;
          --tech-proj-text: #dcfce7;
        }
        .tech-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border-radius: 8px;
          font-weight: 700;
          font-size: 0.85rem;
          letter-spacing: 0.02em;
          color: var(--tech-text);
          background: var(--tech-pill);
          border: 1px solid var(--tech-border);
        }
        .tech-badge.tech {
          background: var(--tech-tech-bg);
          border-color: var(--tech-tech-border);
          color: var(--tech-tech-text);
        }
        .tech-badge.project {
          background: var(--tech-proj-bg);
          border-color: var(--tech-proj-border);
          color: var(--tech-proj-text);
        }
        .tech-name { font-weight: 600; color: var(--tech-text); }
        .tech-status { font-size: 0.8rem; color: var(--tech-muted); margin-top: 2px; }
        .tech-cost {
          text-align: right;
          font-family: "Consolas", "Courier New", monospace;
          font-variant-numeric: tabular-nums;
          color: var(--tech-text);
          font-size: 0.6rem;
        }
        .tech-dim { opacity: 0.45; }
        .tech-header {
          text-transform: uppercase;
          font-size: 0.72rem;
          letter-spacing: 0.08em;
          color: var(--tech-muted);
          margin-bottom: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    sort_mode = st.radio(
        "Order within category",
        ("Tech cost (desc)", "Friendly name (A-Z)"),
        horizontal=True,
    )

    filters: GraphFilters = st.session_state.filters
    completed = set(st.session_state.completed)
    backlog_set = set(st.session_state.backlog)

    grouped = {}
    for node in nodes.values():
        is_visible = _matches_filters(node, completed, backlog_set, filters)
        if filters.hide_filtered and not is_visible:
            continue
        category = node.category or "Uncategorized"
        grouped.setdefault(category, []).append((node, is_visible))

    if not grouped:
        st.caption("No items match the current filters.")
        return

    for category in sorted(grouped.keys()):
        st.markdown(f"**{category}**")
        header_cols = st.columns([0.1, 0.6, 0.14, 0.08])
        header_cols[0].markdown("<div class='tech-header'>Category</div>", unsafe_allow_html=True)
        header_cols[1].markdown("<div class='tech-header'>Name</div>", unsafe_allow_html=True)
        header_cols[2].markdown("<div class='tech-header' style='text-align:right;'>Cost</div>", unsafe_allow_html=True)
        header_cols[3].markdown("<div class='tech-header' style='text-align:center;'>Add</div>", unsafe_allow_html=True)
        nodes_in_group = grouped[category]
        visibility = {node.identifier: is_visible for node, is_visible in nodes_in_group}
        sorted_nodes = _sort_nodes_for_list([node for node, _ in nodes_in_group], sort_mode)

        for node in sorted_nodes:
            cost_text = _format_cost(_node_cost(node))
            status = []
            if node.identifier in backlog_set:
                status.append("Backlog")
            if node.identifier in completed:
                status.append("Completed")
            if not visibility.get(node.identifier, True):
                status.append("Filtered")

            status_text = ", ".join(status) if status else ""
            disabled = (node.identifier in backlog_set) or not visibility.get(node.identifier, True)
            dim_class = " tech-dim" if not visibility.get(node.identifier, True) else ""
            badge_text = "T" if node.node_type.value == "tech" else "P"
            badge_kind = "tech" if node.node_type.value == "tech" else "project"

            row_cols = st.columns([0.1, 0.6, 0.14, 0.08])
            icon_path = _category_icon_path(node.category)
            if icon_path:
                row_cols[0].image(str(icon_path), width=24)
            else:
                row_cols[0].markdown(
                    f"<div class='tech-list-scope tech-name{dim_class}'>{html_escape(node.category or 'Uncategorized')}</div>",
                    unsafe_allow_html=True,
                )
            name_html = f"<div class='tech-name{dim_class}'>{html_escape(node.friendly_name)}</div>"
            if status_text:
                name_html += f"<div class='tech-status{dim_class}'>{html_escape(status_text)}</div>"
            row_cols[1].markdown(f"<div class='tech-list-scope'>{name_html}</div>", unsafe_allow_html=True)
            row_cols[2].markdown(
                f"<div class='tech-list-scope tech-cost{dim_class}'>{cost_text}</div>",
                unsafe_allow_html=True,
            )
            row_cols[3].button(
                "✅" if node.identifier in backlog_set else "➕",
                key=f"list-{node.identifier}",
                on_click=apply_backlog_addition,
                args=(node.identifier,),
                width="stretch",
                disabled=disabled,
            )


def render_backlog(nodes):
    st.subheader("Backlog")
    st.caption("Drag and drop to reorder. Use the list to add items.")
    backlog = st.session_state.backlog

    if not backlog:
        st.caption("No backlog items yet.")
        return

    order_value = st.text_input(
        "Backlog order",
        value=json.dumps(backlog),
        key="backlog_order",
        label_visibility="collapsed",
    )
    st.markdown(
        "<style>input[aria-label='Backlog order'] { display: none; }</style>",
        unsafe_allow_html=True,
    )
    new_order = _parse_backlog_order(order_value, backlog)
    if new_order is not None and new_order != backlog:
        st.session_state.backlog = new_order
        backlog = new_order
        st.session_state.backlog_order = json.dumps(backlog)

    _render_sortable_backlog(backlog, nodes)

    remove_map = {}
    for node_id in backlog:
        label = f"{_friendly_name(node_id, nodes)} [{node_id}]"
        remove_map[label] = node_id

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


def render_completion(nodes):
    st.subheader("Completion state")
    st.caption("Mark items you've already finished to de-emphasize them.")
    options = _option_choices(nodes)
    default_labels = [label for label, node_id in options.items() if node_id in st.session_state.completed]
    selected = st.multiselect("Completed items", options=list(options.keys()), default=default_labels)
    st.session_state.completed = {options[name] for name in selected}


def render_graph(explorer, nodes):
    st.subheader("Graph explorer")
    st.caption("Hover for details, select a node to focus prerequisites and dependents.")

    options = _option_choices(nodes)
    option_labels = ["None"] + list(options.keys())
    default_label = next((label for label, node_id in options.items() if node_id == st.session_state.selected), "None")
    selected_label = st.selectbox("Focus node", option_labels, index=option_labels.index(default_label))
    st.session_state.selected = options.get(selected_label)

    graph_view = explorer.build_view(
        selected=st.session_state.selected,
        completed=st.session_state.completed,
        backlog=st.session_state.backlog,
        filters=st.session_state.filters,
    )

    graphviz_spec = build_graphviz(graph_view)
    st.graphviz_chart(graphviz_spec, width="stretch")

    with st.expander("Selection details", expanded=bool(st.session_state.selected)):
        if st.session_state.selected:
            node = nodes.get(st.session_state.selected)
            st.markdown(f"**{node.friendly_name}** ({node.node_type.value.title()})")
            st.write(f"Category: {node.category or 'Uncategorized'}")
            if node.prereqs:
                prereq_labels = ", ".join(_friendly_name(pid, nodes) for pid in node.prereqs)
                st.write(f"Prerequisites: {prereq_labels}")
            if node.metadata:
                st.json(node.metadata)

            st.button("Quick-add to backlog", on_click=apply_backlog_addition, args=(node.identifier,), type="primary")
        else:
            st.caption("Select a node to see its dependencies and metadata.")

    with st.expander("Graph debug data"):
        st.write("Filters", asdict(st.session_state.filters))
        st.write("Selected", st.session_state.selected)
        st.write("Completed", list(st.session_state.completed))
        st.write("Backlog", st.session_state.backlog)


def main():
    st.set_page_config(
        page_title="Terra Invicta Tech Planner",
        layout="wide",
        page_icon="ĐYs?",
    )
    st.title("Terra Invicta Tech Planner")
    st.caption("Browse the full tech and project list, build a backlog, then proceed to results.")

    hero_cols = st.columns(3)
    with hero_cols[0]:
        st.markdown("**Data source**")
        st.write(INPUT_DIR)
    with hero_cols[1]:
        if st.button("Reload data", type="secondary", width="stretch"):
            st.session_state.reload_token += 1
            st.cache_data.clear()
            st.rerun()
    with hero_cols[2]:
        st.markdown("Need help? See [user stories](docs/user_stories.md) for expected flows.")

    load_report = load_inputs(st.session_state.get("reload_token", 0))

    if load_report.errors:
        st.error("Encountered errors while loading inputs:")
        for error in load_report.errors:
            st.write(f"- {error}")
        st.stop()

    ensure_state(load_report.nodes)

    validation_result = validate_graph(load_report.nodes)
    render_validation(validation_result)
    if validation_result.has_errors:
        st.stop()

    node_count = len(load_report.nodes)
    tech_count = sum(1 for node in load_report.nodes.values() if node.node_type.value == "tech")
    project_count = node_count - tech_count

    metric_cols = st.columns(3)
    metric_cols[0].metric("Total nodes", node_count)
    metric_cols[1].metric("Techs", tech_count)
    metric_cols[2].metric("Projects", project_count)

    cols = st.columns([1, 1.5], gap="large")
    with cols[0]:
        render_filters(load_report.nodes)
        st.divider()
        render_completion(load_report.nodes)
        st.divider()
        render_backlog(load_report.nodes)

    with cols[1]:
        st.subheader("Next step")
        st.caption("Run the calculation and open the results view.")
        if st.button("Proceed with calculation", type="primary", width="stretch"):
            st.session_state.calculation_requested = True
            st.switch_page("pages/Results.py")
        if st.button("Open graph explorer", type="secondary", width="stretch"):
            st.switch_page("pages/Graph.py")
        st.divider()
        render_node_list(load_report.nodes)


if __name__ == "__main__":
    main()

