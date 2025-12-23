# Design: Immutable graph + flat planner views

## Overview

We optimize for planner-page responsiveness by separating concerns:

1. **Graph data** (nodes + edges + adjacency) is built once after load + validation and then treated as immutable.
2. **Flat list model** (fields required to render the list quickly) is built once and then treated as immutable.
3. **Filter view** is an immutable projection over the flat list (primarily index-based) created on demand.
4. **Backlog state** is a separate, minimal structure referencing the immutable base list (by index), supporting fast membership checks and reorder.

This mirrors common UI architecture: immutable “model” + small mutable “state” that only contains user choices.

## Data Model

The exact shapes can evolve during implementation, but the intent is:

### Immutable graph core

- **`GraphData`** (frozen):
  - `node_ids: tuple[str, ...]` (stable order)
  - `id_to_index: dict[str, int]` (fast lookup)
  - `node_type: tuple[NodeType, ...]`
  - `category: tuple[str | None, ...]`
  - `friendly_name: tuple[str, ...]`
  - `prereqs: tuple[tuple[int, ...], ...]` (indices)
  - `dependents: tuple[tuple[int, ...], ...]` (indices)
  - Optional: `metadata_compact: tuple[dict[str, Any], ...]` or a curated subset of fields used in UI.

Immutability guideline: store sequences as tuples; avoid exposing mutable lists; treat dicts as internal and never mutated after build.

### Immutable flat list model (planner list)

- **`FlatNodeRow`** (frozen):

  - `index: int` (position in `GraphData`)
  - `node_id: str`
  - `friendly_name: str`
  - `friendly_name_casefold: str` (precomputed for sorting/search)
  - `node_type: NodeType`
  - `category: str | None`
  - `cost: int | None` (pre-parsed from metadata where present)
  - Any other precomputed display fields currently used in `main.py`.

- **`FlatNodeList`** (frozen):
  - `rows: tuple[FlatNodeRow, ...]`
  - `category_to_indices: dict[str, tuple[int, ...]]` (pre-grouped)
  - `sorted_indices_by_name: tuple[int, ...]`
  - `sorted_indices_by_cost_desc: tuple[int, ...]` (or per-category versions)

Key idea: the planner list should not repeatedly compute derived fields (e.g., cost parsing, sort keys, label formatting).

### Immutable filter view

- **`ListFilterState`** (frozen-ish state input):

  - categories
  - include_completed/include_incomplete
  - backlog_only
  - (no dimming mode; excluded rows are simply not included)

- **`FlatListView`** (immutable projection):
  - `visible_indices: tuple[int, ...]`

The view is constructed from:

- `FlatNodeList`
- `completed_set` (mutable user state)
- `backlog_membership` (mutable user state)
- `ListFilterState`

The view must not mutate the base list.

### Backlog structure

- **`BacklogState`** (mutable only at the top-level session state):
  - `order: tuple[int, ...]` (node indices)
  - `members: frozenset[int]` (fast membership)

Operations:

- add: append index if absent
- remove: filter order tuple; rebuild members
- reorder: accept new order tuple; rebuild members

## Streamlit Integration

Current code uses `st.session_state` for:

- `filters`, `backlog`, `completed`, `selected`, `reload_token`

Proposed structure:

- `st.session_state.graph_data: GraphData` (rebuilt only when reload_token changes)
- `st.session_state.flat_list: FlatNodeList` (derived from GraphData; rebuilt only on reload)
- `st.session_state.completed: set[int]` (indices, not IDs)
- `st.session_state.backlog_state: BacklogState` (order + members)
- `st.session_state.filters: ListFilterState` (or keep `GraphFilters` but treat as input-only)

Critical: keep all heavy transforms (building GraphData + FlatNodeList) behind the reload token so UI interactions do not rebuild them.

## Planner Page Focus

We prioritize the planner page performance:

- The “Technology and project list” should render using flat rows and precomputed groupings.
- Filter toggles should only rebuild a lightweight `visible_indices` view structure, not the base list.
- Backlog operations should update `BacklogState` only.

Other pages:

- Graph page can keep `GraphExplorer` for now, but should consume the immutable graph representation if feasible.

## Compatibility / Migration

- Keep `InputLoader` and `GraphValidator` behavior unchanged.
- Introduce a transformation step after validation:
  - `LoadReport.nodes (dict[str, Node])` → `GraphData` + `FlatNodeList`
- Gradually refactor UI code:
  - Convert list rendering to use `FlatNodeList` and `FlatListView`.
  - Convert backlog/completed tracking to index-based storage.

## Testing Plan

- Unit tests for:
  - building `GraphData` from nodes
  - building `FlatNodeList` and its sort/group invariants
  - filter view creation correctness (visibility rules)
  - backlog operations (add/remove/reorder)
- Integration-ish test for:
  - reload token rebuilds immutable structures; filter toggles do not

## Risks

- Index-based state requires careful mapping from node IDs; ensure stable `id_to_index` and rebuild user state on reload.
- Streamlit session state serialization/hashing: avoid storing unserializable objects in cache; prefer pure dataclasses/tuples.
- Avoid premature micro-optimizations that harm readability; keep performance wins targeted to hot paths (planner list + filters).
