"""Core package for Terra Invicta tech optimizer utilities."""

from .graph import (
    GraphEdgeView,
    GraphExplorer,
    GraphFilters,
    GraphNodeStyle,
    GraphNodeView,
    GraphView,
)
from .input_loader import InputLoader, LoadReport, Node, NodeType
from .backlog_storage import (
    DecodedBacklog,
    decode_backlog,
    encode_backlog,
    indices_for_ids,
)
from .planner_data import (
    BacklogState,
    FlatListView,
    FlatNodeList,
    FlatNodeRow,
    GraphData,
    ListFilters,
    backlog_add,
    backlog_remove,
    backlog_reorder,
    build_flat_list_view,
    build_flat_node_list,
    build_graph_data,
    explode_backlog,
)
from .simulation import (
    SimulationConfig,
    SimulationResult,
    SimulationSlotConfig,
    TurnSnapshot,
    simulate_research,
)
from .validation import GraphValidator, ValidationIssue, ValidationResult

__all__ = [
    "InputLoader",
    "LoadReport",
    "Node",
    "NodeType",
    "GraphValidator",
    "ValidationIssue",
    "ValidationResult",
    "GraphExplorer",
    "GraphView",
    "GraphNodeView",
    "GraphEdgeView",
    "GraphFilters",
    "GraphNodeStyle",
    "GraphData",
    "FlatNodeRow",
    "FlatNodeList",
    "FlatListView",
    "ListFilters",
    "BacklogState",
    "build_graph_data",
    "build_flat_node_list",
    "build_flat_list_view",
    "explode_backlog",
    "backlog_add",
    "backlog_remove",
    "backlog_reorder",
    "encode_backlog",
    "decode_backlog",
    "DecodedBacklog",
    "indices_for_ids",
    "SimulationConfig",
    "SimulationSlotConfig",
    "SimulationResult",
    "TurnSnapshot",
    "simulate_research",
]
