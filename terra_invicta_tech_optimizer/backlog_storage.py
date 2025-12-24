"""Helpers for persisting backlog state to browser storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .planner_data import BacklogState, GraphData

STORAGE_KEY = "ti-planner-backlog"
STORAGE_VERSION = 1


@dataclass(frozen=True, slots=True)
class DecodedBacklog:
    backlog: BacklogState
    dropped: tuple[str, ...]


def encode_backlog(graph_data: GraphData, backlog: BacklogState) -> dict:
    """Translate backlog indices into a versioned storage payload."""

    order = [graph_data.node_ids[idx] for idx in backlog.order if 0 <= idx < graph_data.size]
    return {"version": STORAGE_VERSION, "order": order}


def decode_backlog(payload: object, graph_data: GraphData) -> DecodedBacklog | None:
    """Rebuild backlog state from a storage payload.

    Invalid shapes or versions return ``None`` to signal caller should
    ignore the stored value.
    """

    if not isinstance(payload, dict):
        return None

    if payload.get("version") != STORAGE_VERSION:
        return None

    order_value = payload.get("order")
    if not isinstance(order_value, list):
        return None

    seen: set[int] = set()
    indices: list[int] = []
    dropped: list[str] = []

    for item in order_value:
        if not isinstance(item, str):
            return None
        idx = graph_data.id_to_index.get(item)
        if idx is None:
            dropped.append(item)
            continue
        if idx in seen:
            continue
        seen.add(idx)
        indices.append(idx)

    backlog = BacklogState(order=tuple(indices), members=frozenset(indices))
    return DecodedBacklog(backlog=backlog, dropped=tuple(dropped))


def indices_for_ids(ids: Iterable[str], graph_data: GraphData) -> tuple[int, ...]:
    """Map node identifiers to indices, dropping unknown values."""

    indices: list[int] = []
    for item in ids:
        idx = graph_data.id_to_index.get(item)
        if idx is None:
            continue
        indices.append(idx)
    return tuple(indices)
