# planner-backlog-persistence Specification

## ADDED Requirements
### Requirement: Load backlog from browser storage on app open
The planner SHALL attempt to hydrate the backlog from browser `localStorage` when the Start here page loads, falling back to the current in-memory backlog when storage is empty, invalid, or references unknown nodes.

#### Scenario: Restore backlog from localStorage
- **GIVEN** a user previously saved backlog state in `localStorage`
- **WHEN** the user opens or refreshes the Start here page
- **THEN** the backlog in Streamlit session state SHALL initialize with the stored order and membership
- **AND** items that no longer exist in the current graph SHALL be ignored while preserving the remaining order

#### Scenario: Invalid storage data falls back safely
- **GIVEN** the `localStorage` entry is missing, malformed JSON, or contains data of the wrong shape
- **WHEN** the Start here page initializes backlog state
- **THEN** the planner SHALL ignore the stored value and continue with the default empty/backed-up backlog without crashing

### Requirement: Keep backlog changes synchronized to browser storage
The planner SHALL persist backlog changes into browser `localStorage` whenever items are added, removed, or reordered from any page that edits the backlog.

#### Scenario: Backlog edits persist automatically
- **GIVEN** the user adds or reorders backlog items on the Start here page
- **WHEN** the backlog state updates
- **THEN** the planner SHALL write the current backlog (order + membership identifiers) to `localStorage` within the same interaction
- **AND** subsequent reloads SHALL reflect the updated order without additional user action

#### Scenario: Cross-page backlog edits remain consistent
- **GIVEN** another page (e.g., Graph) provides a way to add or remove backlog items
- **WHEN** the backlog changes from that page
- **THEN** the stored backlog in `localStorage` SHALL be updated so that returning to Start here shows the same state

### Requirement: Storage format is versioned and minimal
The persisted backlog payload SHALL be versioned and contain only stable node identifiers/order needed to rebuild backlog membership, allowing safe evolution of the format.

#### Scenario: Versioned payload supports future changes
- **GIVEN** the planner writes backlog data to `localStorage`
- **THEN** the payload SHALL include a version marker and a list of node identifiers in priority order
- **AND** future format changes SHALL be able to detect and migrate/ignore older versions without data corruption

### Requirement: Storage operations remain transparent to the user
Backlog persistence SHALL remain unobtrusive, with optional messaging only when recovery or mismatches occur.

#### Scenario: User is informed when storage data is partially applied
- **GIVEN** stored backlog data omits or references nodes not present in the current graph
- **WHEN** the backlog initializes
- **THEN** the planner MAY display a non-blocking notice summarizing dropped items while continuing with the remaining backlog

#### Scenario: No extra controls required
- **GIVEN** backlog persistence is automatic
- **WHEN** the user interacts with Start here or other backlog controls
- **THEN** no additional toggle is required to opt-in; storage reads/writes occur behind the scenes using the existing backlog UI
