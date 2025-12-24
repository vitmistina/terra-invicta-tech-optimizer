from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from terra_invicta_tech_optimizer import (
    NodeType,
    SimulationConfig,
    SimulationSlotConfig,
    explode_backlog,
    simulate_research,
)


def ensure_simulation_defaults() -> None:
    st.session_state.setdefault("simulation_project_slots", 1)
    st.session_state.setdefault("simulation_tech_pips", [3, 3, 3])
    st.session_state.setdefault("simulation_project_pips", [1, 1, 1])


def render_simulation_controls(graph_data) -> SimulationConfig:
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
                f"Tech {idx + 1} pips",
                value=int(st.session_state.simulation_tech_pips[idx]),
                min_value=0,
                max_value=3,
            )
        tech_pips.append(int(value))
    st.session_state.simulation_tech_pips = tech_pips

    project_cols = st.columns(project_slots)
    project_pips: list[int] = []
    for idx, col in enumerate(project_cols):
        with col:
            default = st.session_state.simulation_project_pips[idx]
            value = st.number_input(
                f"Project {idx + 1} pips",
                value=int(default),
                min_value=0,
                max_value=3,
            )
        project_pips.append(int(value))
    while len(project_pips) < 3:
        project_pips.append(0)
    st.session_state.simulation_project_pips = project_pips

    return build_simulation_config(graph_data)


def build_simulation_config(graph_data) -> SimulationConfig:
    tech_slots = tuple(
        SimulationSlotConfig(
            name=f"Tech {idx + 1}", node_type=NodeType.TECH, pips=pips
        )
        for idx, pips in enumerate(st.session_state.simulation_tech_pips)
    )
    project_slots = tuple(
        SimulationSlotConfig(
            name=f"Project {idx + 1}", node_type=NodeType.PROJECT, pips=pips
        )
        for idx, pips in enumerate(
            st.session_state.simulation_project_pips[
                : st.session_state.simulation_project_slots
            ]
        )
    )

    backlog_state = st.session_state.backlog_state
    completed = frozenset(st.session_state.completed)
    exploded_backlog = explode_backlog(
        graph_data, backlog_state.order, set(completed)
    )

    return SimulationConfig(
        backlog_order=exploded_backlog,
        completed=completed,
        tech_slots=tech_slots,
        project_slots=project_slots,
    )


def run_simulation(graph_data, *, costs, friendly_names, categories, config: SimulationConfig):
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


def _build_backlog_dataframe(flat_list, order: tuple[int, ...], completed: set[int]) -> pd.DataFrame:
    rows = []
    for position, index in enumerate(order, start=1):
        row = flat_list.rows[index]
        rows.append(
            {
                "Order": position,
                "Name": row.friendly_name,
                "Type": row.node_type.value,
                "Category": row.category or "Uncategorized",
                "Researched": index in completed,
                "Node ID": row.node_id,
            }
        )
    return pd.DataFrame(rows)


def render_backlog_dataframes(graph_data, *, flat_list) -> None:
    st.subheader("Backlog details")
    backlog_state = st.session_state.backlog_state
    if not backlog_state.order:
        st.caption("No backlog items yet.")
        return

    completed = set(st.session_state.completed)
    backlog_df = _build_backlog_dataframe(flat_list, backlog_state.order, completed)
    st.markdown("**Backlog order**")
    st.dataframe(backlog_df, use_container_width=True, hide_index=True)

    exploded_order = explode_backlog(
        graph_data, backlog_state.order, completed
    )
    exploded_df = _build_backlog_dataframe(flat_list, exploded_order, completed)
    st.markdown("**Exploded backlog (with prerequisites)**")
    st.dataframe(exploded_df, use_container_width=True, hide_index=True)


def render_category_mix(result) -> None:
    st.subheader("Category mix over time")

    if not result.turns:
        st.info("Add backlog items to view simulation output.")
        return

    view_mode = st.radio("View mode", ("Per turn", "Cumulative"), horizontal=True)
    mix_source = result.cumulative_mix if view_mode == "Cumulative" else result.category_mix

    rows = []
    for turn_index, sample in enumerate(mix_source, start=1):
        for category, proportion in sample.items():
            rows.append(
                {
                    "turn": turn_index,
                    "category": category,
                    "proportion": proportion,
                }
            )

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


def render_timeline(result) -> None:
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
        label_map = {
            f"{rec['label']} ({rec['slot']})": rec["node_id"] for rec in selectable
        }
        choice = st.selectbox("Highlight on graph", ["None"] + list(label_map.keys()))
        if choice != "None":
            st.session_state.selected = label_map.get(choice)
            st.info("Selection saved. Open the Graph page to view the highlight.")
