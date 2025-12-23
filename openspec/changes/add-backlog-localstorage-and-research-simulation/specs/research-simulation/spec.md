# research-simulation Specification

## ADDED Requirements
### Requirement: Simulate research with tech and project slots
The planner SHALL simulate research progress using three tech slots and user-configurable project slots (1–3) that consume backlog items in order while respecting dependencies and pip allocations.

#### Scenario: Slots respect backlog order and dependencies
- **GIVEN** a backlog ordered by priority on the Start here page
- **WHEN** the simulation runs
- **THEN** tech slots SHALL fill first, project slots SHALL take remaining eligible backlog items, and any item with unmet prerequisites SHALL be skipped until prerequisites are completed

#### Scenario: Pip allocation drives proportional progress
- **GIVEN** the user sets 0–3 pips per tech slot and per project slot
- **WHEN** the simulation divides research output
- **THEN** progress per slot SHALL be proportional to assigned pips (e.g., 1 pip vs 3 pips yields 25% vs 75%) and SHALL apply to item cost/duration to determine turn-by-turn completion

#### Scenario: Turn-level output is emitted
- **GIVEN** the simulation processes backlog items over time
- **WHEN** an item starts or completes
- **THEN** the simulation output SHALL list, per turn, which items occupy each slot and which items finish that turn

### Requirement: Show category mix over time
The planner SHALL visualize how research time is distributed across tech categories as the simulated timeline advances, updating whenever backlog or simulation parameters change.

#### Scenario: Category proportions per turn are charted
- **GIVEN** simulation results with per-turn slot assignments and node categories
- **WHEN** the user views the category mix chart
- **THEN** a stacked area or bar chart SHALL show per-turn proportions of total active research time by category, with hover details showing category, active items, and cumulative totals

#### Scenario: Cumulative view is available
- **GIVEN** the category mix chart is rendered
- **WHEN** the user toggles or selects a cumulative view
- **THEN** the chart SHALL display cumulative category proportions over time using the same data source

### Requirement: Display slot utilization timeline
The planner SHALL render a timeline showing, per turn, which item occupies each tech and project slot, including idle periods, and keep it synchronized with backlog/simulation changes.

#### Scenario: Slots mapped on timeline with idle markers
- **GIVEN** simulation output with turn-by-turn slot assignments
- **WHEN** the user opens the slot utilization view
- **THEN** the x-axis SHALL represent turns and the y-axis SHALL list tech/project slots
- **AND** each slot SHALL show bars for assigned items and explicit markers for idle turns

#### Scenario: Timeline is interactive and linked to graph
- **GIVEN** the user clicks a bar representing an item on the timeline
- **WHEN** the interaction occurs
- **THEN** the corresponding node SHALL be highlighted in the dependency graph view (or queued for highlight on next graph render)

#### Scenario: Visualization stays in sync with backlog edits
- **GIVEN** the user modifies backlog order or slot/pip parameters
- **WHEN** the simulation recomputes
- **THEN** the category mix chart and slot utilization timeline SHALL refresh to reflect the updated plan without manual reload
