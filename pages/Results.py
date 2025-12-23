from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from terra_invicta_tech_optimizer import (
    NodeType,
    SimulationConfig,
    SimulationSlotConfig,
    simulate_research,
)

from main import (
    INPUT_DIR,
    ensure_state,
    get_models,
    hydrate_backlog_from_storage,
    load_inputs,
    render_validation,
    validate_graph,
)


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

    _ensure_simulation_defaults()

    _, flat_list = get_models(load_report.nodes)
    costs = {row.index: row.cost for row in flat_list.rows}
    friendly_names = {row.index: row.friendly_name for row in flat_list.rows}
    categories = {row.index: row.category or "Uncategorized" for row in flat_list.rows}

    config = _render_simulation_controls()

    stored_result = st.session_state.get("simulation_result")
    stored_config = st.session_state.get("simulation_config")
    config_changed = stored_config is not None and stored_config != config

    run_requested = st.button("Run simulation", type="primary")
    should_run = run_requested or stored_result is None

    if should_run:
        result = _run_simulation(
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

    _render_category_mix(result)
    _render_timeline(result)

    st.subheader("Graph explorer")
    st.info("The interactive graph has moved to the Graph page.")
    if st.button("Open graph explorer", type="primary", width="stretch"):
        st.switch_page("pages/Graph.py")


def _ensure_simulation_defaults() -> None:
    st.session_state.setdefault("simulation_project_slots", 1)
    st.session_state.setdefault("simulation_tech_pips", [3, 3, 3])
    st.session_state.setdefault("simulation_project_pips", [1, 1, 1])


def _render_simulation_controls() -> SimulationConfig:
    st.subheader("Simulation inputs")
    st.caption("Adjust slots and pips, then run the simulation to refresh results.")

    project_slots = st.slider(
        "Project slots", 1, 3, value=st.session_state.simulation_project_slots
    )
    st.session_state.simulation_project_slots = project_slots

    tech_cols = st.columns(3)
    tech_pips: list[int] = []
    for idx, col in enumerate(tech_cols):
        with col:
            value = st.number_input(
                f"Tech {idx + 1} pips", value=int(st.session_state.simulation_tech_pips[idx]), min_value=0, max_value=3
            )
        tech_pips.append(int(value))
    st.session_state.simulation_tech_pips = tech_pips

    project_cols = st.columns(project_slots)
    project_pips: list[int] = []
    for idx, col in enumerate(project_cols):
        with col:
            default = st.session_state.simulation_project_pips[idx]
            value = st.number_input(
                f"Project {idx + 1} pips", value=int(default), min_value=0, max_value=3
            )
        project_pips.append(int(value))
    while len(project_pips) < 3:
        project_pips.append(0)
    st.session_state.simulation_project_pips = project_pips

    return _build_simulation_config()


def _build_simulation_config() -> SimulationConfig:
    tech_slots = tuple(
        SimulationSlotConfig(name=f"Tech {idx + 1}", node_type=NodeType.TECH, pips=pips)
        for idx, pips in enumerate(st.session_state.simulation_tech_pips)
    )
    project_slots = tuple(
        SimulationSlotConfig(name=f"Project {idx + 1}", node_type=NodeType.PROJECT, pips=pips)
        for idx, pips in enumerate(st.session_state.simulation_project_pips[: st.session_state.simulation_project_slots])
    )

    backlog_state = st.session_state.backlog_state
    completed = frozenset(st.session_state.completed)

    return SimulationConfig(
        backlog_order=backlog_state.order,
        completed=completed,
        tech_slots=tech_slots,
        project_slots=project_slots,
    )


def _run_simulation(
    graph_data,
    *,
    costs,
    friendly_names,
    categories,
    config: SimulationConfig,
):
    result = simulate_research(
        graph_data,
        costs=costs,
        friendly_names=friendly_names,
        categories=categories,
        config=config,
    )
    st.session_state.simulation_result = result
    st.session_state.simulation_config = config
    return result


def _render_category_mix(result):
    st.subheader("Category mix over time")

    if not result.turns:
        st.info("Add backlog items to view simulation output.")
        return

    view_mode = st.radio("View mode", ("Per turn", "Cumulative"), horizontal=True)
    mix_source = result.cumulative_mix if view_mode == "Cumulative" else result.category_mix

    rows = []
    for turn_index, sample in enumerate(mix_source, start=1):
        for category, proportion in sample.items():
            rows.append({"turn": turn_index, "category": category, "proportion": proportion})

    if not rows:
        st.caption("No active research slots for selected configuration.")
        return

    df = pd.DataFrame(rows)
    chart = (
        alt.Chart(df)
        .mark_area()
        .encode(
            x=alt.X("turn:Q", title="Turn"),
            y=alt.Y("proportion:Q", stack="normalize", title="Proportion"),
            color=alt.Color("category:N", title="Category"),
            tooltip=["turn", "category", alt.Tooltip("proportion", format=".0%")],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_timeline(result) -> None:
    st.subheader("Slot utilization")

    if not result.turns:
        st.caption("No timeline to display yet.")
        return

    records = []
    slot_names = [slot.slot for slot in result.turns[0].slots]
    last_turn = result.turns[-1].turn + 1

    for slot_name in slot_names:
        current_label: str | None = None
        current_id: str | None = None
        start_turn = 1
        for snapshot in result.turns:
            slot_state = next(item for item in snapshot.slots if item.slot == slot_name)
            label = slot_state.friendly_name or (slot_state.node_id or "Idle")
            node_id = slot_state.node_id
            category = slot_state.category or "Uncategorized"
            if current_label is None:
                current_label = label
                current_id = node_id
                start_turn = snapshot.turn
                continue
            if label != current_label or node_id != current_id:
                records.append(
                    {
                        "slot": slot_name,
                        "label": current_label,
                        "node_id": current_id,
                        "start": start_turn,
                        "end": snapshot.turn,
                        "category": category,
                    }
                )
                current_label = label
                current_id = node_id
                start_turn = snapshot.turn
        if current_label is not None:
            records.append(
                {
                    "slot": slot_name,
                    "label": current_label,
                    "node_id": current_id,
                    "start": start_turn,
                    "end": last_turn,
                    "category": category,
                }
            )

    df = pd.DataFrame(records)

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("start:Q", title="Turn"),
            x2="end",
            y=alt.Y("slot:N", title="Slot"),
            color=alt.Color("category:N", title="Category"),
            tooltip=["slot", "label", "start", "end", "category"],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)

    selectable = [rec for rec in records if rec.get("node_id")]
    if selectable:
        label_map = {f"{rec['label']} ({rec['slot']})": rec["node_id"] for rec in selectable}
        choice = st.selectbox("Highlight on graph", ["None"] + list(label_map.keys()))
        if choice != "None":
            st.session_state.selected = label_map.get(choice)
            st.info("Selection saved. Open the Graph page to view the highlight.")


if __name__ == "__main__":
    main()
