# Implementation Plan: add-backlog-localstorage-and-research-simulation

## Objective
Translate the OpenSpec requirements for backlog localStorage persistence and research simulation into a concrete implementation approach that slots into the existing Streamlit app and core models.

## Context
- Backlog is currently held only in `st.session_state.backlog_state` (seeded from legacy `backlog`/`completed` keys) with no browser persistence or cross-page sync beyond Streamlit state.
- There is no research simulation pipeline; `Start_here.py` captures backlog ordering and navigates to the results page without turn-level projections.
- Specs to satisfy:
  - `planner-backlog-persistence/spec.md`: load from localStorage on open, auto-sync edits, versioned/minimal payload, unobtrusive UX.
  - `research-simulation/spec.md`: simulate tech/project slots with pip weighting, surface category mix, and slot utilization timeline with graph linkage.

## Backlog persistence implementation
1. **Storage shape and versioning**
   - Persist JSON at a stable key (e.g., `ti-planner-backlog`). Payload: `{ "version": 1, "order": [<node_id strings>] }`.
   - When hydrating, accept only `version == 1` and `order` array of strings; unknown versions or malformed content fall back to empty/previous state.

2. **Hydration on Start here load**
   - Add a lightweight Streamlit component (`components.html` or `st_js_eval`-style helper) that reads the localStorage key and returns parsed JSON to Python via `st.session_state`/`st.experimental_data_editor` pattern.
   - After `ensure_state` computes `GraphData`, map stored node IDs to indices; drop unknown IDs while preserving the provided order. If any drop occurs, enqueue a dismissible `st.info` banner noting ignored items (non-blocking per spec).
   - Guard against invalid JSON/shape by logging a debug message and skipping the storage payload.

3. **Continuous sync on backlog mutation**
   - Wrap backlog mutations (`apply_backlog_addition`, `remove_backlog_item`, reorder handler) so they trigger a `persist_backlog()` helper that serializes the current `order` -> node IDs and pushes to localStorage via the same component.
   - Ensure updates fire from any page that edits backlog (Start here + Graph): centralize helper in `main.py` that other pages can import.
   - Debounce writes within a session interaction (e.g., single `components.html` call per render) to avoid unnecessary reruns.

4. **Resilience and transparency**
   - If storage write errors occur (e.g., browser blocks storage), surface a one-time warning banner but allow in-memory backlog to continue.
   - Keep UI unchanged otherwise; no new toggles or opt-in controls.

5. **Testing hooks**
   - Expose pure functions for translating between `BacklogState` and storage payload for unit tests (e.g., `encode_backlog(graph_data, backlog_state) -> dict`, `decode_backlog(payload, graph_data) -> BacklogState | None`).
   - Add integration test using mocked component return to ensure hydration handles bad data and missing nodes.

## Research simulation implementation
1. **Configuration and inputs**
   - Create a dedicated module (e.g., `terra_invicta_tech_optimizer/simulation.py`) defining:
     - `SimulationConfig`: tech slots fixed at 3; project slots configurable 1–3; pip allocations per slot (0–3); backlog order (node IDs/indices).
     - `SimulationResult`: per-turn slot occupancy, completion events, and derived category proportions.
   - Source node metadata (cost/category/type/dependencies) from existing `GraphData`/flat list to avoid duplicate parsing.

2. **Scheduling algorithm**
   - Maintain separate queues for tech and project candidates derived from backlog order while respecting unmet prerequisites.
   - Each turn:
     - Fill tech slots first, then project slots from remaining eligible backlog entries.
     - Advance progress per slot proportionally to assigned pips; when progress >= cost, mark completion, free slot, and attempt to schedule next eligible backlog item.
     - Record per-turn snapshot of slot → node assignments and completions.
   - Skip nodes with unmet prerequisites until prerequisites complete; if no eligible node fits a slot, mark the slot idle that turn.

3. **Results for visualization**
   - Emit timeline structure consumable by Streamlit (list of turns with slot states). Include node IDs, friendly names, categories, and type (tech/project) for labeling.
   - Derive category mix per turn from active slots; compute cumulative proportions to power both standard and cumulative chart views.
   - Provide mapping from node ID → turn(s) + slot for interactivity with the graph page (highlight/scroll on click).

4. **UI integration (Start here / Results)**
   - Extend Start here or Results page to capture simulation inputs (project slot count, pip allocations). Default pips could mirror current UI defaults (e.g., 3 per tech slot, 1 per project slot) with validation on 0–3 range.
   - Add Streamlit charts:
     - Stacked area/bar for per-turn category proportions with toggle for cumulative view.
     - Timeline (e.g., Plotly Gantt-style or altair layered bars) showing each slot over turns, idle markers, and click callbacks to push selected node ID to shared session state for graph highlighting.
   - Recompute simulation reactively when backlog order, completed set, or slot/pip parameters change.

5. **Testing strategy**
   - Unit tests for scheduler covering: dependency gating, pip weighting (e.g., 1 vs 3 pips), idle-slot handling, and deterministic ordering from backlog priority.
   - Snapshot-style test for category mix aggregation and timeline serialization to ensure chart inputs stay stable.

## Rollout and validation
- Add docstring-level references to the corresponding OpenSpec requirements to keep traceability.
- Validate specs with `openspec validate add-backlog-localstorage-and-research-simulation --strict` once tooling is available locally.
- Implementation complete when backlog persists across reloads with versioned payloads and simulation outputs drive both category mix and slot timeline views in sync with backlog edits.
