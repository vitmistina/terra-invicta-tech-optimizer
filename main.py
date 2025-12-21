from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import streamlit as st

from terra_invicta_tech_optimizer import (
    GraphExplorer,
    GraphFilters,
    GraphValidator,
    InputLoader,
)


INPUT_DIR = Path(__file__).parent / "inputs"

st.set_page_config(
    page_title="Terra Invicta Tech Planner",
    layout="wide",
    page_icon="🚀",
)


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


def reorder_backlog(node_id: str, direction: int):
    backlog = st.session_state.backlog
    if node_id not in backlog:
        return
    idx = backlog.index(node_id)
    new_index = max(0, min(len(backlog) - 1, idx + direction))
    if new_index == idx:
        return
    backlog[idx], backlog[new_index] = backlog[new_index], backlog[idx]


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
    st.caption("Focus the graph on categories, completion state, or backlog.")

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


def render_backlog(nodes):
    st.subheader("Backlog management")
    st.caption("Build and reorder your priority queue. Items here gain emphasis in the graph.")
    backlog = st.session_state.backlog

    options = _option_choices(nodes)
    option_labels = ["Select a node"] + list(options.keys())
    selected_label = st.selectbox("Add item", option_labels)
    node_to_add = options.get(selected_label)

    add_cols = st.columns([2, 1])
    with add_cols[0]:
        st.button("Add to backlog", on_click=apply_backlog_addition, args=(node_to_add,), width="stretch")
    with add_cols[1]:
        st.button("Remove", on_click=remove_backlog_item, args=(node_to_add,), width="stretch")

    if backlog:
        st.markdown("**Priority order**")
        for idx, node_id in enumerate(backlog):
            label = _friendly_name(node_id, nodes)
            cols = st.columns([4, 1, 1, 1])
            cols[0].write(f"{idx + 1}. {label}")
            with cols[1]:
                st.button(
                    "⬆️",
                    key=f"up-{node_id}",
                    on_click=reorder_backlog,
                    args=(node_id, -1),
                    width="stretch",
                )
            with cols[2]:
                st.button(
                    "⬇️",
                    key=f"down-{node_id}",
                    on_click=reorder_backlog,
                    args=(node_id, 1),
                    width="stretch",
                )
            with cols[3]:
                st.button(
                    "Remove",
                    key=f"drop-{node_id}",
                    on_click=remove_backlog_item,
                    args=(node_id,),
                    width="stretch",
                    type="secondary",
                )
    else:
        st.caption("No backlog items yet.")


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
    st.title("Terra Invicta Tech Planner")
    st.caption("Explore the Terra Invicta tech tree, filter by focus, and curate your priority backlog.")

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

    explorer = get_explorer(load_report.nodes)
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
        render_graph(explorer, load_report.nodes)


if __name__ == "__main__":
    main()

