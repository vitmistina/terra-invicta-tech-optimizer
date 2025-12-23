# Change: Refactor immutable graph + planner data views

## Why

The first (planner) page performs repeated work while users interact with filters, the tech/project list, and backlog controls. For large Terra Invicta datasets, that extra computation (and repeated Python object churn) harms responsiveness.

This change makes the loaded/validated graph immutable and introduces flatter, cache-friendly data structures for list rendering, filter views, and backlog state. The goal is to reduce recomputation and memory churn so UI interactions remain fast.

## What Changes

- After input loading and validation succeed, the graph is converted into an **immutable** in-memory representation that is treated as read-only until the next reload.
- The “Technology and project list” uses a **flat, efficient list model** (immutable) designed specifically for rendering and filtering.
- Applying filters produces a **separate immutable view** over the flat list using `visible_indices` (no per-row dimming), without mutating the base list.
- Backlog is represented as a **separate, efficient structure** (order + membership) that references the immutable base list (e.g., by index), without copying node payloads.
- The initial (planner) page is the primary performance target; other pages may be updated only as needed for consistency.

## Non-Goals (for now)

- No new optimization/scheduling engine.
- No new UX features beyond preserving current behavior.
- No UI redesign; focus is internal structure and responsiveness.

## Impact

- Affected user flows: planner page load, list rendering, filter toggles, backlog add/remove/reorder, completion state marking.
- Likely affected code:
  - `main.py` (state management and list rendering)
  - `terra_invicta_tech_optimizer/` (new immutable models / helpers)
  - `tests/` (new unit tests around immutability + views)

## Success Criteria

- Interactions on the planner page (toggling filters, adding/removing backlog items) do not trigger reload/validation and complete with minimal latency.
- The immutable graph/list/backlog structures make it difficult (or impossible) to accidentally mutate shared state.
- Existing behaviors remain intact (filters, backlog operations, graph focus selection).
