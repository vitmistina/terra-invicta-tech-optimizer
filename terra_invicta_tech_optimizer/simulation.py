"""Research simulation engine for tech and project backlogs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

from .input_loader import NodeType
from .planner_data import GraphData


@dataclass(frozen=True, slots=True)
class SimulationSlotConfig:
    name: str
    node_type: NodeType
    pips: int


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    backlog_order: tuple[int, ...]
    completed: frozenset[int]
    tech_slots: tuple[SimulationSlotConfig, ...]
    project_slots: tuple[SimulationSlotConfig, ...]


@dataclass(frozen=True, slots=True)
class SlotState:
    slot: str
    node_index: int | None
    node_id: str | None
    friendly_name: str | None
    category: str | None
    node_type: NodeType | None
    pips: int
    remaining_cost: float | None


@dataclass(frozen=True, slots=True)
class CompletionEvent:
    node_index: int
    node_id: str
    turn_completed: int
    slot: str


@dataclass(frozen=True, slots=True)
class TurnSnapshot:
    turn: int
    slots: tuple[SlotState, ...]
    completed: tuple[CompletionEvent, ...]


@dataclass(frozen=True, slots=True)
class SimulationResult:
    turns: tuple[TurnSnapshot, ...]
    category_mix: tuple[dict[str, float], ...]
    cumulative_mix: tuple[dict[str, float], ...]


def _cost_for_index(index: int, *, costs: Mapping[int, int | None]) -> float:
    cost = costs.get(index)
    if cost is None:
        return 1.0
    try:
        parsed = float(cost)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return 1.0
    return max(parsed, 1.0)


def simulate_research(
    graph_data: GraphData,
    *,
    costs: Mapping[int, int | None],
    friendly_names: Mapping[int, str],
    categories: Mapping[int, str | None],
    config: SimulationConfig,
) -> SimulationResult:
    """Run a deterministic turn-based research simulation."""

    backlog_order = tuple(idx for idx in config.backlog_order if 0 <= idx < graph_data.size)
    completed: set[int] = set(idx for idx in config.completed if 0 <= idx < graph_data.size)

    slot_configs = list(config.tech_slots + config.project_slots)
    slots_progress: list[float | None] = [None for _ in slot_configs]
    slots_assignment: list[int | None] = [None for _ in slot_configs]

    prereqs_map = {idx: set(prereqs) for idx, prereqs in enumerate(graph_data.prereqs)}
    turns: list[TurnSnapshot] = []
    node_types = graph_data.node_type

    def _find_candidate(target_type: NodeType, in_progress: set[int]) -> int | None:
        for idx in backlog_order:
            if idx in completed or idx in in_progress:
                continue
            if idx < 0 or idx >= graph_data.size:
                continue
            if node_types[idx] != target_type:
                continue
            prereq_indices = prereqs_map.get(idx, set())
            if prereq_indices and not prereq_indices.issubset(completed):
                continue
            return idx
        return None

    turn = 1
    while True:
        in_progress_indices = {idx for idx in slots_assignment if idx is not None}

        for slot_idx, slot_cfg in enumerate(slot_configs):
            if slots_assignment[slot_idx] is not None:
                continue
            candidate = _find_candidate(slot_cfg.node_type, in_progress_indices)
            if candidate is None:
                continue
            slots_assignment[slot_idx] = candidate
            slots_progress[slot_idx] = _cost_for_index(candidate, costs=costs)
            in_progress_indices.add(candidate)

        active_assignments = [
            (
                idx,
                slots_assignment[idx],
                slots_progress[idx],
                slot_configs[idx],
            )
            for idx in range(len(slot_configs))
            if slots_assignment[idx] is not None
        ]

        progress_candidates = [
            remaining / slot_cfg.pips
            for _, _, remaining, slot_cfg in active_assignments
            if remaining is not None and slot_cfg.pips > 0
        ]

        if not progress_candidates:
            if not active_assignments:
                break

            # No progress possible (e.g., zero pips). Capture the stalled state and exit.
            snapshot_slots = [
                SlotState(
                    slot=slot_cfg.name,
                    node_index=slots_assignment[idx],
                    node_id=(graph_data.node_ids[slots_assignment[idx]] if slots_assignment[idx] is not None else None),
                    friendly_name=(
                        friendly_names.get(slots_assignment[idx])
                        if slots_assignment[idx] is not None
                        else None
                    ),
                    category=(
                        categories.get(slots_assignment[idx])
                        if slots_assignment[idx] is not None
                        else None
                    ),
                    node_type=(
                        node_types[slots_assignment[idx]]
                        if slots_assignment[idx] is not None
                        else None
                    ),
                    pips=slot_cfg.pips,
                    remaining_cost=slots_progress[idx],
                )
                for idx, slot_cfg in enumerate(slot_configs)
            ]

            turns.append(
                TurnSnapshot(
                    turn=turn,
                    slots=tuple(snapshot_slots),
                    completed=tuple(),
                )
            )
            break

        tick = min(progress_candidates)

        snapshot_slots: list[SlotState] = []
        completed_events: list[CompletionEvent] = []

        for slot_idx, slot_cfg in enumerate(slot_configs):
            node_index = slots_assignment[slot_idx]
            remaining = slots_progress[slot_idx]
            node_id: str | None = None
            friendly_name: str | None = None
            category: str | None = None
            node_type: NodeType | None = None
            remaining_after = remaining

            if node_index is not None:
                node_id = graph_data.node_ids[node_index]
                friendly_name = friendly_names.get(node_index)
                category = categories.get(node_index)
                node_type = node_types[node_index]

                if remaining is not None:
                    remaining_after = remaining - (slot_cfg.pips * tick)
                    if remaining_after <= 0:
                        completed.add(node_index)
                        completed_events.append(
                            CompletionEvent(
                                node_index=node_index,
                                node_id=node_id,
                                turn_completed=turn,
                                slot=slot_cfg.name,
                            )
                        )
                        slots_assignment[slot_idx] = None
                        slots_progress[slot_idx] = None
                        remaining_after = 0.0
                    else:
                        slots_progress[slot_idx] = remaining_after

            snapshot_slots.append(
                SlotState(
                    slot=slot_cfg.name,
                    node_index=node_index,
                    node_id=node_id,
                    friendly_name=friendly_name,
                    category=category,
                    node_type=node_type,
                    pips=slot_cfg.pips,
                    remaining_cost=remaining_after,
                )
            )

        turns.append(
            TurnSnapshot(
                turn=turn,
                slots=tuple(snapshot_slots),
                completed=tuple(completed_events),
            )
        )

        if not any(idx is not None for idx in slots_assignment):
            candidate_remaining = _find_candidate(NodeType.TECH, set()) or _find_candidate(NodeType.PROJECT, set())
            if candidate_remaining is None:
                break

        turn += 1

        if turn > graph_data.size + 50:
            break

    category_mix = _build_category_mix(turns)
    cumulative_mix = _build_cumulative_mix(category_mix)

    return SimulationResult(
        turns=tuple(turns),
        category_mix=tuple(category_mix),
        cumulative_mix=tuple(cumulative_mix),
    )


def _build_category_mix(turns: Iterable[TurnSnapshot]) -> list[dict[str, float]]:
    mix: list[dict[str, float]] = []
    for turn in turns:
        counter: Counter[str] = Counter()
        total_weight = 0
        for slot in turn.slots:
            if slot.node_index is None or slot.category is None:
                continue
            weight = max(slot.pips, 0)
            if weight == 0:
                continue
            counter[slot.category] += weight
            total_weight += weight
        if total_weight == 0:
            mix.append({})
            continue
        mix.append({category: value / total_weight for category, value in counter.items()})
    return mix


def _build_cumulative_mix(mix: Iterable[dict[str, float]]) -> list[dict[str, float]]:
    cumulative: Counter[str] = Counter()
    snapshots: list[dict[str, float]] = []

    for sample in mix:
        for category, value in sample.items():
            cumulative[category] += value
        snapshots.append(dict(cumulative))
    return snapshots
