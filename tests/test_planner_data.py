from terra_invicta_tech_optimizer import (
    BacklogState,
    ListFilters,
    Node,
    NodeType,
    backlog_add,
    backlog_remove,
    backlog_reorder,
    build_flat_list_view,
    build_flat_node_list,
    build_graph_data,
)


def sample_nodes():
    return {
        "TechA": Node(
            identifier="TechA",
            friendly_name="Tech A",
            node_type=NodeType.TECH,
            category="Energy",
            prereqs=[],
            metadata={"researchCost": 120},
        ),
        "TechB": Node(
            identifier="TechB",
            friendly_name="Tech B",
            node_type=NodeType.TECH,
            category="Social",
            prereqs=["TechA"],
            metadata={"researchCost": "50"},
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


def test_build_graph_data_has_stable_indices_and_adjacency():
    nodes = sample_nodes()
    graph = build_graph_data(nodes)

    assert graph.id_to_index["TechA"] < graph.id_to_index["TechB"]
    assert graph.prereqs[graph.id_to_index["TechB"]] == (graph.id_to_index["TechA"],)
    assert graph.prereqs[graph.id_to_index["Proj1"]] == (graph.id_to_index["TechB"],)

    assert graph.dependents[graph.id_to_index["TechA"]] == (graph.id_to_index["TechB"],)
    assert graph.dependents[graph.id_to_index["TechB"]] == (graph.id_to_index["Proj1"],)


def test_flat_node_list_precomputes_cost_and_categories():
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    assert set(flat_list.categories) >= {"Energy", "Social", "Space"}

    techa = flat_list.rows[graph.id_to_index["TechA"]]
    techb = flat_list.rows[graph.id_to_index["TechB"]]
    proj1 = flat_list.rows[graph.id_to_index["Proj1"]]

    assert techa.cost == 120
    assert techb.cost == 50
    assert proj1.cost is None


def test_build_flat_list_view_uses_visible_indices_only():
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    completed = {graph.id_to_index["TechA"]}
    backlog = {graph.id_to_index["TechB"]}

    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(
            categories=frozenset({"Energy", "Social"}),
            include_completed=False,
            include_incomplete=True,
            backlog_only=False,
        ),
        completed=completed,
        backlog_members=backlog,
        sort_mode="Friendly name (A-Z)",
    )

    visible = set(view.visible_indices)
    assert graph.id_to_index["TechA"] not in visible
    assert graph.id_to_index["TechB"] in visible
    assert graph.id_to_index["Proj1"] not in visible


def test_backlog_state_operations_are_minimal_and_correct():
    state = BacklogState()
    state = backlog_add(state, 2)
    state = backlog_add(state, 1)
    state = backlog_add(state, 2)

    assert state.order == (2, 1)
    assert state.members == frozenset({1, 2})

    state = backlog_remove(state, 2)
    assert state.order == (1,)
    assert state.members == frozenset({1})

    state = backlog_add(state, 3)
    state = backlog_add(state, 4)
    state = backlog_reorder(state, [4, 3, 999, 1])
    assert state.order == (4, 3, 1)
    assert state.members == frozenset({1, 3, 4})


def test_search_query_filters_by_friendly_name_only():
    """Test that search_query filters only by friendly_name (case-insensitive substring)."""
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    # Search for "Tech" - should match "Tech A" and "Tech B" but not "Project One"
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query="Tech"),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    visible = set(view.visible_indices)
    assert graph.id_to_index["TechA"] in visible
    assert graph.id_to_index["TechB"] in visible
    assert graph.id_to_index["Proj1"] not in visible


def test_search_query_is_case_insensitive():
    """Test that search is case-insensitive."""
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    # Search with lowercase "project" should match "Project One"
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query="project"),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    visible = set(view.visible_indices)
    assert graph.id_to_index["Proj1"] in visible
    assert graph.id_to_index["TechA"] not in visible


def test_search_query_substring_match():
    """Test that search uses substring matching."""
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    # Search for "One" should match "Project One"
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query="One"),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    visible = set(view.visible_indices)
    assert graph.id_to_index["Proj1"] in visible


def test_search_query_does_not_match_id_or_category():
    """Test that search does NOT match node_id or category, only friendly_name."""
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    # Search for "TechA" (node ID) should not match anything
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query="TechA"),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    assert len(view.visible_indices) == 0

    # Search for "Energy" (category) should not match anything
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query="Energy"),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    assert len(view.visible_indices) == 0


def test_search_query_with_whitespace_is_trimmed():
    """Test that leading/trailing whitespace in search query is handled."""
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    # Search with whitespace should still match
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query="  Tech  "),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    visible = set(view.visible_indices)
    assert graph.id_to_index["TechA"] in visible
    assert graph.id_to_index["TechB"] in visible


def test_search_query_empty_shows_all():
    """Test that empty or None search_query shows all items."""
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    # None search_query
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query=None),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    assert len(view.visible_indices) == 3

    # Empty string
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(search_query=""),
        completed=set(),
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    assert len(view.visible_indices) == 3


def test_search_query_combined_with_other_filters():
    """Test that search works correctly when combined with other filters."""
    nodes = sample_nodes()
    graph = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph, nodes)

    completed = {graph.id_to_index["TechA"]}

    # Search for "Tech" + exclude completed -> should only show TechB
    view = build_flat_list_view(
        flat_list,
        filters=ListFilters(
            search_query="Tech",
            include_completed=False,
            include_incomplete=True,
        ),
        completed=completed,
        backlog_members=set(),
        sort_mode="Friendly name (A-Z)",
    )
    visible = set(view.visible_indices)
    assert graph.id_to_index["TechB"] in visible
    assert graph.id_to_index["TechA"] not in visible
    assert graph.id_to_index["Proj1"] not in visible
