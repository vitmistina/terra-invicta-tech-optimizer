from terra_invicta_tech_optimizer import (
    BacklogState,
    Node,
    NodeType,
    build_graph_data,
    decode_backlog,
    encode_backlog,
)


def _graph_data():
    nodes = {
        "alpha": Node(identifier="alpha", friendly_name="Alpha", node_type=NodeType.TECH, category="Energy"),
        "beta": Node(identifier="beta", friendly_name="Beta", node_type=NodeType.PROJECT, category="Space"),
    }
    return build_graph_data(nodes)


def test_encode_decode_round_trip():
    graph_data = _graph_data()
    backlog = BacklogState(order=(0, 1), members=frozenset({0, 1}))

    payload = encode_backlog(graph_data, backlog)
    decoded = decode_backlog(payload, graph_data)

    assert decoded is not None
    assert decoded.backlog.order == backlog.order
    assert decoded.dropped == ()


def test_decode_drops_unknown_ids():
    graph_data = _graph_data()
    payload = {"version": 1, "order": ["alpha", "missing", "beta"]}

    decoded = decode_backlog(payload, graph_data)

    assert decoded is not None
    assert decoded.backlog.order == (0, 1)
    assert decoded.dropped == ("missing",)


def test_decode_invalid_version_returns_none():
    graph_data = _graph_data()
    payload = {"version": 99, "order": ["alpha"]}

    assert decode_backlog(payload, graph_data) is None
