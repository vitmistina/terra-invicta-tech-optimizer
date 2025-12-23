from __future__ import annotations

import streamlit as st

from main import (
    INPUT_DIR,
    ensure_state,
    get_models,
    get_explorer,
    hydrate_backlog_from_storage,
    load_inputs,
    persist_backlog_storage,
    render_backlog,
    render_completion,
    render_filters,
    render_graph,
    render_validation,
    validate_graph,
)


st.set_page_config(
    page_title="Terra Invicta Tech Planner - Graph",
    layout="wide",
)


def main():
    st.title("Graph Explorer")
    st.caption("Explore dependencies with interactive highlighting and filters.")

    nav_cols = st.columns(2)
    with nav_cols[0]:
        if st.button("Back to planner", type="secondary", width="stretch"):
            st.switch_page("main.py")
    with nav_cols[1]:
        if st.button("Go to results", type="secondary", width="stretch"):
            st.switch_page("pages/Results.py")

    if "reload_token" not in st.session_state:
        st.session_state.reload_token = 0

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
        st.markdown(
            "Need help? See [user stories](docs/user_stories.md) for expected flows."
        )

    load_report = load_inputs(st.session_state.get("reload_token", 0))

    if load_report.errors:
        st.error("Encountered errors while loading inputs:")
        for error in load_report.errors:
            st.write(f"- {error}")
        st.stop()

    graph_data, _ = get_models(load_report.nodes)
    ensure_state(load_report.nodes, graph_data=graph_data)
    hydrate_backlog_from_storage(graph_data)

    validation_result = validate_graph(load_report.nodes)
    render_validation(validation_result)
    if validation_result.has_errors:
        st.stop()

    explorer = get_explorer(load_report.nodes)
    node_count = len(load_report.nodes)
    tech_count = sum(
        1 for node in load_report.nodes.values() if node.node_type.value == "tech"
    )
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
