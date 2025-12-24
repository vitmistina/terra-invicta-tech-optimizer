from terra_invicta_tech_optimizer import (
    Node,
    NodeType,
    SimulationConfig,
    SimulationSlotConfig,
    build_graph_data,
    simulate_research,
)


def _sample_graph():
    nodes = {
        "alpha": Node(
            identifier="alpha",
            friendly_name="Alpha",
            node_type=NodeType.TECH,
            category="Energy",
            metadata={"researchCost": 3},
        ),
        "beta": Node(
            identifier="beta",
            friendly_name="Beta",
            node_type=NodeType.PROJECT,
            category="Space",
            prereqs=["alpha"],
            metadata={"researchCost": 4},
        ),
    }
    return build_graph_data(nodes), nodes


def test_simulation_respects_dependencies_and_pips():
    graph_data, nodes = _sample_graph()
    costs = {idx: nodes[node_id].metadata["researchCost"] for idx, node_id in enumerate(graph_data.node_ids)}
    friendly = {idx: nodes[node_id].friendly_name for idx, node_id in enumerate(graph_data.node_ids)}
    categories = {idx: nodes[node_id].category for idx, node_id in enumerate(graph_data.node_ids)}

    config = SimulationConfig(
        backlog_order=(graph_data.id_to_index["alpha"], graph_data.id_to_index["beta"]),
        completed=frozenset(),
        tech_slots=(SimulationSlotConfig(name="Tech 1", node_type=NodeType.TECH, pips=3),),
        project_slots=(SimulationSlotConfig(name="Project 1", node_type=NodeType.PROJECT, pips=1),),
    )

    result = simulate_research(
        graph_data,
        costs=costs,
        friendly_names=friendly,
        categories=categories,
        config=config,
    )

    assert result.turns[0].slots[1].node_index is None  # project waits for prereq
    completion_ids = [event.node_id for turn in result.turns for event in turn.completed]
    assert completion_ids == ["alpha", "beta"]


def test_category_mix_accumulates():
    graph_data, nodes = _sample_graph()
    costs = {idx: nodes[node_id].metadata["researchCost"] for idx, node_id in enumerate(graph_data.node_ids)}
    friendly = {idx: nodes[node_id].friendly_name for idx, node_id in enumerate(graph_data.node_ids)}
    categories = {idx: nodes[node_id].category for idx, node_id in enumerate(graph_data.node_ids)}

    config = SimulationConfig(
        backlog_order=tuple(graph_data.id_to_index.values()),
        completed=frozenset(),
        tech_slots=(SimulationSlotConfig(name="Tech 1", node_type=NodeType.TECH, pips=1),),
        project_slots=(SimulationSlotConfig(name="Project 1", node_type=NodeType.PROJECT, pips=3),),
    )

    result = simulate_research(
        graph_data,
        costs=costs,
        friendly_names=friendly,
        categories=categories,
        config=config,
    )

    assert len(result.category_mix) == len(result.turns)
    assert result.cumulative_mix[-1]["Energy"] > 0
