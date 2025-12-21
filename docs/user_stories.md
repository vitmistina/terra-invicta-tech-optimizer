# User Stories and Acceptance Criteria

This document breaks down the user-facing requirements for the Terra Invicta tech optimizer Streamlit app. Each story includes a short description and acceptance criteria that clarify what “done” looks like.

## Input loading and validation

### US-01: Load tech and project data from `inputs/`
- **As a** player
- **I want** the app to ingest tech and project definitions from structured files in the `inputs` directory
- **So that** I can work with the current game data without manual entry
- **Acceptance criteria**
  - Files in `inputs/` are read on app start or when the user clicks “Reload data”.
  - Supported formats (JSON/CSV/TSV) are documented and validated; unsupported files are ignored with a warning.
  - Parsed nodes are tagged as Tech or Project and capture type/category metadata when available.

### US-02: Validate the DAG before use
- **As a** player
- **I want** the app to verify that the dependency graph is acyclic and complete
- **So that** I avoid planning with invalid data
- **Acceptance criteria**
  - Cycle detection runs on load; errors are shown with the offending nodes/edges.
  - Missing references (dependencies that are not defined) are reported with node names.
  - Projects must depend on at least one tech; violations are flagged as errors.
  - Validation results are visible in a banner or panel and block downstream planning until resolved.

## Graph exploration and filtering

### US-03: Visualize the dependency graph
- **As a** player
- **I want** an interactive DAG view of techs and projects
- **So that** I can understand prerequisites quickly
- **Acceptance criteria**
  - Nodes are styled by type (Tech vs Project) and tech category (e.g., Social, Energy, Space, Xeno).
  - Zoom/pan interactions are available; hovering shows tooltips with cost, duration, and dependencies.
  - Selecting a node highlights its prerequisites and dependents.

### US-04: Filter and highlight subsets of the graph
- **As a** player
- **I want** to filter nodes by category, completion status, or backlog membership
- **So that** I can focus on relevant parts of the graph
- **Acceptance criteria**
  - Filters can hide or de-emphasize nodes based on category and completion state.
  - Backlog items can be overlaid/highlighted distinctly from non-priority nodes.
  - A reset control clears all filters and returns to the full graph.

## Backlog management

### US-05: Build and reorder a priority queue
- **As a** player
- **I want** to select techs/projects and order them by priority
- **So that** the optimizer reflects my strategy
- **Acceptance criteria**
  - Multi-select control lists all available nodes with search and category tags.
  - Drag-and-drop (or up/down controls) changes the priority order.
  - Projects can only be added if they reference at least one tech in the graph; invalid additions show an error.
  - Backlog state persists in the session when navigating between views.

### US-06: Quick-add backlog items from the graph
- **As a** player
- **I want** to add items to the backlog directly from the graph view
- **So that** I can capture priorities as I explore dependencies
- **Acceptance criteria**
  - Node context menu or click action offers “Add to backlog”.
  - When added, the backlog list updates immediately and the node is highlighted as prioritized.
  - Duplicate additions are prevented with a friendly notice.

## Slot-constrained optimization

### US-07: Simulate research with tech and project slots
- **As a** player
- **I want** the app to fill my three tech slots first, then apply remaining slots to the next backlog items
- **So that** I get an optimal research path that matches Terra Invicta rules
- **Acceptance criteria**
  - Three tech slots are always available; project slots range from one to three based on a user-controlled game stage parameter.
  - The scheduler respects dependencies, durations/costs, and current backlog order.
  - If a priority item is blocked by unmet prerequisites, the optimizer skips to the next available item without idling tech slots unnecessarily.
  - Output includes a turn-by-turn list of started and completed items with slot assignments.

### US-08: Apply research speed and scenario parameters
- **As a** player
- **I want** to adjust research speed multipliers and slot counts
- **So that** I can test different scenarios
- **Acceptance criteria**
  - Controls let me set research speed modifiers for techs and projects independently.
  - Changing parameters triggers a re-run of the optimizer and updates all dependent views.
  - A comparison indicator notes when results differ from the previous run.

## Progression insights

### US-09: Show category mix over time
- **As a** player
- **I want** a chart of how research time is split across tech categories as the timeline progresses
- **So that** I can balance my portfolio
- **Acceptance criteria**
  - A stacked area or bar chart shows category proportions by turn or phase.
  - Hovering reveals category, active items, and cumulative totals for the selected turn.
  - Data updates when backlog or scenario parameters change.

### US-10: Display slot utilization timeline
- **As a** player
- **I want** a turn-by-turn view of what occupies each slot
- **So that** I can see overlaps, idle time, and critical path items
- **Acceptance criteria**
  - Timeline maps turns on the x-axis and slots on the y-axis for both techs and projects.
  - Idle slots are explicitly marked; clicking a bar highlights the corresponding node in the graph.
  - View stays in sync with optimizer output and backlog changes.

## Scenario persistence and guidance

### US-11: Save and load planning scenarios
- **As a** player
- **I want** to export and import my backlog and parameters
- **So that** I can revisit or share plans easily
- **Acceptance criteria**
  - Export produces a JSON file containing backlog order, slot counts, and research modifiers.
  - Import validates that referenced items exist in the current graph; mismatches are reported with actionable errors.
  - Successful imports immediately update backlog and scenario controls.

### US-12: Surface validation issues and suggestions
- **As a** player
- **I want** clear messages about missing prerequisites or infeasible plans
- **So that** I can correct problems quickly
- **Acceptance criteria**
  - A notification panel summarizes DAG validation errors and backlog issues (e.g., blocked projects).
  - For blocked items, the app suggests prerequisite techs to add.
  - Idle slot warnings indicate when research time is being wasted due to ordering or dependencies.

## Quality and maintainability

### US-13: Automated checks guard correctness
- **As a** maintainer
- **I want** tests and linting to cover loaders, optimizer logic, and chart data
- **So that** regressions are caught early
- **Acceptance criteria**
  - Unit tests cover DAG validation, scheduler edge cases, and visualization data prep.
  - Linting (Ruff) runs cleanly; coverage gates are documented and enforced in CI.
  - Large DAGs load and render within a reasonable time, with caching to avoid redundant computation.
