from __future__ import annotations

import streamlit as st

from terra_invicta_tech_optimizer.streamlit_app.data import get_models, load_inputs, validate_graph
from terra_invicta_tech_optimizer.streamlit_app.state import ensure_state
from terra_invicta_tech_optimizer.streamlit_app.storage import hydrate_backlog_from_storage
from terra_invicta_tech_optimizer.streamlit_app.ui.layout import render_global_styles
from terra_invicta_tech_optimizer.streamlit_app.ui.shared import render_validation
from terra_invicta_tech_optimizer.streamlit_app.ui.start_page import (
    render_backlog_container,
    render_filters_container,
    render_header,
    render_search_box,
    render_technology_list,
    sync_search_from_query_params,
)


st.set_page_config(
    page_title="Terra Invicta Technology Planner - Start Here",
    layout="wide",
    page_icon="🛸",
)

render_global_styles()


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
    sync_search_from_query_params()

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
