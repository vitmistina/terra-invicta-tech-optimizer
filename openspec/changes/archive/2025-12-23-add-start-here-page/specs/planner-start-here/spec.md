## ADDED Requirements

### Requirement: Provide a “Start here” planner page

The system SHALL provide a Streamlit multipage entry titled “Start here” that presents the planner workspace using the wireframe layout from `docs/start-here.drawio.svg`.

#### Scenario: User opens the Start here page

- **GIVEN** the user has launched the Streamlit app
- **WHEN** the user navigates to “Start here”
- **THEN** the page SHALL display a header title and a Search input
- **AND** the page SHALL display a left column containing “Filters” and “Backlog” panels
- **AND** the page SHALL display a main “Technology list” area
- **AND** the page SHALL provide a primary action button labeled “Calculate optimal path” that continues to the results workflow

### Requirement: Start here is the default landing page

When the user launches the Streamlit app, the system SHALL start on the “Start here” page.

#### Scenario: App launch opens Start here

- **GIVEN** the user launches the app via `streamlit run main.py`
- **WHEN** the initial page loads
- **THEN** the user SHALL be shown the “Start here” page

### Requirement: Backlog panel sticks during scrolling

The Start here page SHALL keep the Backlog panel visible by making it stick to the top of the browser window while the user scrolls through long technology lists.

#### Scenario: Backlog remains visible while scrolling

- **GIVEN** the Start here page is displaying a long technology list that requires vertical scrolling
- **WHEN** the user scrolls downward
- **THEN** the Backlog panel SHALL remain pinned near the top of the visible page area

### Requirement: Search filters by Friendly Name only

The Start here page SHALL provide a Search control that filters the technology list using only each item’s Friendly Name.
An item SHALL be included when its Friendly Name contains the Search text as a case-insensitive substring.

#### Scenario: Search matches Friendly Name (case-insensitive)

- **GIVEN** the list contains an item with Friendly Name “Tech A”
- **WHEN** the user enters “tech a” into Search
- **THEN** the list SHALL include “Tech A”

#### Scenario: Search matches substring within Friendly Name

- **GIVEN** the list contains an item with Friendly Name “Project One”
- **WHEN** the user enters “ject o” into Search
- **THEN** the list SHALL include “Project One”

#### Scenario: Search does not match id/category/type

- **GIVEN** a list item’s identifier or category contains the search term but its Friendly Name does not
- **WHEN** the user enters that search term
- **THEN** that item SHALL NOT be included in the filtered list

### Requirement: Search is debounced for responsiveness

The Start here page SHALL debounce Search input such that list filtering begins only after a short period of typing inactivity.

#### Scenario: Filtering waits for inactivity before applying

- **GIVEN** the user is typing into the Search control
- **WHEN** the user pauses typing for at least 200ms
- **THEN** the page SHALL apply filtering using the current Search value

### Requirement: Start here page remains legible in light and dark themes

The Start here page SHALL maintain high-contrast, readable text and controls in both Streamlit light mode and dark mode.

#### Scenario: Light theme readability

- **GIVEN** Streamlit is using a light theme
- **WHEN** the user views the Start here page
- **THEN** the text and controls SHALL be clearly legible with sufficient contrast

#### Scenario: Dark theme readability

- **GIVEN** Streamlit is using a dark theme
- **WHEN** the user views the Start here page
- **THEN** the text and controls SHALL be clearly legible with sufficient contrast

### Requirement: Reuse existing planner components

The Start here page SHALL reuse existing planner rendering components and data models (filters, backlog, list view construction) instead of introducing parallel implementations.

#### Scenario: Shared helper usage

- **GIVEN** the existing planner uses shared rendering helpers and cached models
- **WHEN** the Start here page is implemented
- **THEN** it SHALL call the same helper functions and list-view builders for consistent behavior and performance

### Requirement: Minimize custom CSS

The Start here page SHALL prefer native Streamlit layout and styling.
Any custom CSS SHALL be minimal, locally scoped, and used only when required for specified behaviors (e.g., sticky Backlog) or for the existing drag-and-drop backlog component.

#### Scenario: Default styling is used wherever possible

- **GIVEN** the Start here page is rendered
- **WHEN** the user views the Filters panel and Technology list
- **THEN** the page SHALL use Streamlit’s default styling for typography and colors
- **AND** any custom CSS present SHALL be limited to the minimum needed to satisfy the sticky Backlog and drag-and-drop backlog behaviors
