# planner-performance Specification

## Purpose
TBD - created by archiving change refactor-immutable-graph-data. Update Purpose after archive.
## Requirements
### Requirement: Immutable graph after validation

After input loading and validation succeed, the system SHALL build an immutable in-memory representation of the tech/project graph and treat it as read-only until the next reload.

#### Scenario: Graph becomes read-only after validation

- **GIVEN** inputs have been loaded and the dependency graph has validated successfully
- **WHEN** the user toggles filters, marks completion, or edits the backlog
- **THEN** the underlying graph representation SHALL NOT be rebuilt or mutated

#### Scenario: Reload rebuilds the immutable graph

- **GIVEN** the planner page is open with a validated graph
- **WHEN** the user clicks “Reload data”
- **THEN** the system SHALL reload inputs, re-run validation, and rebuild the immutable graph representation

### Requirement: Flat immutable list model for planner rendering

The system SHALL build a flat, immutable list model derived from the graph that contains all fields needed to render the planner technology/project list efficiently.

#### Scenario: Planner list rendering uses the flat model

- **GIVEN** a validated immutable graph
- **WHEN** the planner list is rendered
- **THEN** the UI SHALL use the flat immutable list model (not recompute per-row derived fields during rendering)

### Requirement: Filter application produces an immutable view

Applying filters SHALL create a separate immutable view over the flat list model without mutating the underlying list model.

#### Scenario: Category filters create a new view

- **GIVEN** a flat immutable list model
- **WHEN** the user selects one or more categories in the filter controls
- **THEN** the system SHALL construct a new filter view exposing `visible_indices` for included rows
- **AND** the underlying flat list model SHALL remain unchanged

#### Scenario: Excluded rows are not rendered

- **GIVEN** the user has selected filters that exclude some nodes
- **WHEN** the list view is constructed
- **THEN** excluded nodes SHALL NOT appear in `visible_indices`

### Requirement: Backlog is stored as a separate efficient structure

The system SHALL represent backlog state using a separate memory-efficient structure that references the immutable list/graph by stable identifiers (preferably indices) and supports fast membership checks.

#### Scenario: Adding to backlog does not copy node payloads

- **GIVEN** a validated immutable graph and flat immutable list model
- **WHEN** the user adds an item to the backlog
- **THEN** backlog state SHALL update by storing a minimal reference (e.g., an index)
- **AND** the flat list and graph structures SHALL NOT be duplicated or mutated

#### Scenario: Reordering backlog updates order only

- **GIVEN** a backlog with multiple items
- **WHEN** the user reorders backlog items
- **THEN** the backlog order structure SHALL update
- **AND** membership checks SHALL remain correct

### Requirement: Planner interactions avoid expensive recomputation

Planner-page interactions (filters, backlog add/remove/reorder, completion state toggles) SHALL avoid re-running input parsing and validation.

#### Scenario: Filter toggles do not re-parse inputs

- **GIVEN** a validated graph
- **WHEN** the user toggles a filter option
- **THEN** input parsing and graph validation SHALL NOT be re-executed

#### Scenario: Backlog updates do not rebuild the base list

- **GIVEN** a flat immutable list model
- **WHEN** the user adds or removes a backlog item
- **THEN** the base list model SHALL NOT be rebuilt

