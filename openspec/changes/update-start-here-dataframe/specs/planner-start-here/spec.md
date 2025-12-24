## ADDED Requirements
### Requirement: Technology list supports category dataframes with icons
The Start here page SHALL allow the technology list to be rendered as category-based tables/dataframes to reduce per-row widget overhead.
Each category section SHALL retain a visual category icon cue in the table context.

#### Scenario: Category dataframe with icon cue
- **GIVEN** the Start here page renders the technology list by category
- **WHEN** a category section is displayed as a table/dataframe
- **THEN** the category section SHALL include the category icon alongside the category label or header

### Requirement: Backlog addition uses selection with a centralized action
When the technology list is rendered as tables/dataframes, the Start here page SHALL allow users to select one or more rows and use a centralized action to add them to the backlog.

#### Scenario: Add selected rows to backlog
- **GIVEN** the user is viewing a category table/dataframe
- **WHEN** the user selects one or more rows and triggers the Add to backlog action
- **THEN** the selected items SHALL be added to the backlog
