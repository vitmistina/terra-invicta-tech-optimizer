from __future__ import annotations

import streamlit as st

from terra_invicta_tech_optimizer.streamlit_app.config import INPUT_DIR
from terra_invicta_tech_optimizer.streamlit_app.data import get_models, load_inputs, validate_graph
from terra_invicta_tech_optimizer.streamlit_app.state import ensure_state
from terra_invicta_tech_optimizer.streamlit_app.storage import hydrate_backlog_from_storage
from terra_invicta_tech_optimizer.streamlit_app.ui.results_page import (
    ensure_simulation_defaults,
    render_backlog_dataframes,
    render_category_mix,
    render_simulation_controls,
    render_timeline,
    run_simulation,
)
from terra_invicta_tech_optimizer.streamlit_app.ui.shared import render_validation


st.set_page_config(
    page_title="Terra Invicta Tech Planner - Results",
    layout="wide",
)


def main():
    st.title("Results")
    st.caption("Calculation output and summaries.")

    if not st.session_state.get("calculation_requested"):
        st.warning(
            "Return to the planner and click 'Proceed with calculation' to view results."
        )
        if st.button("Back to planner", type="secondary", width="stretch"):
            st.switch_page("main.py")
        return

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

    validation_result = validate_graph(load_report.nodes)
    render_validation(validation_result)
    if validation_result.has_errors:
        st.stop()

    node_count = len(load_report.nodes)
    tech_count = sum(
        1 for node in load_report.nodes.values() if node.node_type.value == "tech"
    )
    project_count = node_count - tech_count

    metric_cols = st.columns(3)
    metric_cols[0].metric("Total nodes", node_count)
    metric_cols[1].metric("Techs", tech_count)
    metric_cols[2].metric("Projects", project_count)

    ensure_simulation_defaults()

    _, flat_list = get_models(load_report.nodes)
    costs = {row.index: row.cost for row in flat_list.rows}
    friendly_names = {row.index: row.friendly_name for row in flat_list.rows}
    categories = {row.index: row.category or "Uncategorized" for row in flat_list.rows}

    config = render_simulation_controls(graph_data)

    stored_result = st.session_state.get("simulation_result")
    stored_config = st.session_state.get("simulation_config")
    config_changed = stored_config is not None and stored_config != config

    run_requested = st.button("Run simulation", type="primary")
    should_run = run_requested or stored_result is None

    if should_run:
        result = run_simulation(
            graph_data,
            costs=costs,
            friendly_names=friendly_names,
            categories=categories,
            config=config,
        )
    else:
        result = stored_result

    if config_changed and not should_run:
        st.info("Simulation inputs changed. Click 'Run simulation' to refresh results.")

    if result is None:
        st.info("Run the simulation to view results.")
        return

    render_backlog_dataframes(graph_data, flat_list=flat_list)
    render_category_mix(result)
    render_timeline(result)

    st.subheader("Graph explorer")
    st.info("The interactive graph has moved to the Graph page.")
    if st.button("Open graph explorer", type="primary", width="stretch"):
        st.switch_page("pages/Graph.py")


if __name__ == "__main__":
    main()
