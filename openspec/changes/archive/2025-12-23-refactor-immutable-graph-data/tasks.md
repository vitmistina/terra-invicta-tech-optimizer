## 1. Proposal checklist

- [x] Confirm baseline behavior on planner page (current filters/list/backlog) and record what must remain unchanged.
- [x] Identify which derived fields are recomputed during list rendering and move them into the flat immutable model.

## 2. Core data structures

- [x] Add immutable `GraphData` builder (post-validation) and ensure it contains adjacency info needed for views.
- [x] Add immutable `FlatNodeList` builder optimized for planner list rendering (category grouping + sort keys).

## 3. Views and state

- [x] Implement filter-view constructor producing an immutable `FlatListView` with `visible_indices` from (flat list + user state + filters).
- [x] Implement `BacklogState` operations (add/remove/reorder) referencing node indices.
- [x] Update planner page (`main.py`) to:
  - [x] Build graph/list once per reload token.
  - [x] Store index-based completed/backlog state.
  - [x] Render the list using the flat structures and filter view.

## 4. Validation and reload behavior

- [x] Ensure validation still blocks planning as before.
- [x] Ensure reload rebuilds immutable structures and revalidates.
- [x] Ensure UI interactions do not rebuild graph/list.

## 5. Tests

- [x] Add unit tests for `GraphData`/`FlatNodeList`/view/backlog.
- [x] Update existing tests impacted by state shape changes.

## 6. Docs

- [x] Update README or docs if behavior or developer workflow changes.
