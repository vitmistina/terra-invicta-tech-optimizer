## ADDED Requirements
### Requirement: Results page shows backlog dataframe

The system SHALL display a dataframe on the Results page that lists backlog items in their current order.

#### Scenario: User views backlog dataframe
- **GIVEN** the user has curated a backlog on the Start here page
- **WHEN** the user navigates to the Results page
- **THEN** the page SHALL render a dataframe that repeats the backlog items in the same order as the backlog

### Requirement: Results page shows exploded backlog dataframe

The system SHALL display a second dataframe on the Results page that lists the backlog items plus all prerequisite technologies required to reach them.
The exploded backlog list SHALL deduplicate technologies and avoid expanding dependencies for technologies marked as researched.

#### Scenario: User views exploded backlog with prerequisites
- **GIVEN** the user has a backlog with prerequisite relationships in the graph
- **WHEN** the Results page renders the exploded backlog
- **THEN** the dataframe SHALL include every prerequisite needed for the backlog items
- **AND** each technology SHALL appear only once in the exploded list
- **AND** any technology marked researched SHALL not trigger further prerequisite expansion
