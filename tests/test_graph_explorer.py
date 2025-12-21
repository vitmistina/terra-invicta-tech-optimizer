from terra_invicta_tech_optimizer import GraphExplorer, GraphFilters, Node, NodeType


def sample_nodes():
    return {
        "TechA": Node(
            identifier="TechA",
            friendly_name="Tech A",
            node_type=NodeType.TECH,
            category="Energy",
            prereqs=[],
            metadata={"cost": 120},
        ),
        "TechB": Node(
            identifier="TechB",
            friendly_name="Tech B",
            node_type=NodeType.TECH,
            category="Social",
            prereqs=["TechA"],
            metadata={"duration": 3},
        ),
        "Proj1": Node(
            identifier="Proj1",
            friendly_name="Project One",
            node_type=NodeType.PROJECT,
            category="Space",
            prereqs=["TechB"],
            metadata={},
        ),
    }


def test_build_view_highlights_dependencies_and_status():
    explorer = GraphExplorer(sample_nodes())

    view = explorer.build_view(selected="Proj1", completed={"TechA"}, backlog={"TechB"})
    nodes = {node.identifier: node for node in view.nodes}

    assert nodes["Proj1"].is_selected is True
    assert nodes["TechB"].is_prerequisite is True
    assert nodes["TechA"].is_prerequisite is True
    assert nodes["TechA"].is_completed is True
    assert nodes["TechB"].in_backlog is True

    assert nodes["TechA"].style.shape == "dot"
    assert nodes["Proj1"].style.shape == "square"
    assert nodes["TechA"].style.color != nodes["TechB"].style.color

    highlighted_edges = [edge for edge in view.edges if edge.is_highlighted]
    assert ("TechB", "Proj1") in {(edge.source, edge.target) for edge in highlighted_edges}
    assert ("TechA", "TechB") in {(edge.source, edge.target) for edge in highlighted_edges}


def test_filters_hide_or_dim_nodes_and_edges():
    explorer = GraphExplorer(sample_nodes())
    filters = GraphFilters(categories={"Energy"}, hide_filtered=True)

    view = explorer.build_view(filters=filters)
    nodes = {node.identifier: node for node in view.nodes}

    assert nodes["TechA"].is_hidden is False
    assert nodes["TechB"].is_hidden is True
    assert nodes["Proj1"].is_hidden is True

    edges = {(edge.source, edge.target): edge for edge in view.edges}
    assert edges[("TechA", "TechB")].is_hidden is True
    assert edges[("TechB", "Proj1")].is_hidden is True

    filters.hide_filtered = False
    view_dimmed = explorer.build_view(filters=filters)
    nodes_dimmed = {node.identifier: node for node in view_dimmed.nodes}
    assert nodes_dimmed["TechB"].is_dimmed is True
    assert nodes_dimmed["Proj1"].is_dimmed is True


def test_reset_filters_restores_full_graph():
    explorer = GraphExplorer(sample_nodes())
    filters = GraphFilters(categories={"Space"}, backlog_only=True, hide_filtered=True)

    filtered_view = explorer.build_view(filters=filters, backlog={"Proj1"})
    assert all(node.is_hidden for node in filtered_view.nodes if node.identifier != "Proj1")

    reset_view = explorer.build_view(filters=GraphFilters.reset())
    assert all(node.is_hidden is False for node in reset_view.nodes)
    assert all(edge.is_hidden is False for edge in reset_view.edges)
