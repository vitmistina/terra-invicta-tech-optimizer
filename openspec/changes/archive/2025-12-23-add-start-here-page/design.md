## Context

The repository is a Streamlit multipage app with a planner entrypoint in `main.py` and additional pages in `pages/` that import shared helpers from `main.py` (see `pages/Graph.py`, `pages/Results.py`).

The wireframe in `docs/start-here.drawio.svg` depicts a “Start here” page with:

- Header title: “Terra Invicta Technology Planner”
- A Search box on the right
- Left column with “FILTERS” above “BACKLOG”
- Main “TECHNOLOGY LIST” area
- A primary action button “Calculate optimal path” contained withing the BACKLOG panel on its bottom
- A specific behavior note: Backlog “sticks to the top of the container, even as technology list scrolls…”, interpreted as **sticky to the top of the browser viewport** while the long list scrolls.

The current planner (`main.py`) already contains most of these components but:

- Has no dedicated search input.
- Does not make backlog sticky during page scroll.
- Uses some custom CSS that is strongly dark-theme oriented and may not be legible in light theme.

## Goals

- Implement a new Streamlit page “Start here” that matches the wireframe layout.
- Make the user start on the “Start here” page when launching the app.
- Add a search feature that filters by **Friendly Name only**.
- Make search feel responsive by debouncing filtering until the user pauses typing.
- Make backlog sticky at the top as the user scrolls the list.
- Maintain high contrast / legibility in both Streamlit light and dark themes.
- Reuse existing components and data models (avoid a parallel implementation).
- Minimize custom CSS and rely on Streamlit defaults where possible.

## Non-Goals

- No fuzzy search, stemming, regex search, or searching across category/id/type.
- No new optimizer algorithm changes beyond wiring the existing “proceed” flow.
- No new persistence model beyond existing Streamlit session state.

## Decisions

### 0) Default landing page

Users should start on “Start here”.

Proposed approach:

- Keep `pages/Start_here.py` as the wireframe-aligned page.
- Update `main.py` to immediately route/redirect to `pages/Start_here.py` (or convert `main.py` into the Start here page) so Streamlit’s default entry opens Start here.

### 1) Where search filtering lives

Search SHOULD be applied in the same place list filtering is computed today to keep performance predictable.

Proposed approach:

- Extend `ListFilters` in `terra_invicta_tech_optimizer/planner_data.py` with an optional `search_query: str | None`.
- Apply it inside `build_flat_list_view(...)` using `FlatNodeRow.friendly_name_casefold` for a case-insensitive substring match.

This keeps the list filtering logic pure and testable, and reuses the already-precomputed `friendly_name_casefold` field.

### 2) “Friendly Name only” semantics

The list filter MUST match only against `friendly_name`.

- Case-insensitive substring match: include an item when its Friendly Name contains the (trimmed) search query.
- No matching on `node_id`, category, or node type.

### 2.1) Debounce semantics

Filtering SHOULD NOT be applied on every keystroke. The Search control SHOULD apply filtering only after a short period of inactivity (debounce window), so typing remains fast and the app avoids unnecessary reruns.

Proposed approach:

- Implement Search input as a small embedded HTML/JS component that updates Streamlit state only after a debounce delay (reusing the existing hidden-input + JS pattern used for backlog ordering).
- Use a default debounce window of ~250ms.

### 3) Sticky backlog behavior

Backlog should stay visible at the top as users scroll through long content.

Proposed approach:

- Wrap the backlog panel in a scoped HTML container and apply CSS `position: sticky` with a top offset.
- Keep selectors as stable and locally scoped as possible to reduce Streamlit DOM brittleness.

### 3.1) Minimize custom CSS (“out of box”)

Prefer Streamlit primitives and default styling for layout, typography, and colors.

Custom CSS should be used only when Streamlit does not provide a native equivalent:

- Sticky backlog behavior (`position: sticky`).
- Hiding technical helper input(s) used for JS → Streamlit state handoff.
- The existing drag-and-drop backlog component’s minimal styling (theme-safe variables/fallbacks).

The Start here “Technology list” should avoid bespoke CSS-heavy styling.

### 4) Theme legibility (high contrast)

Avoid hard-coding colors that only work in one theme.

Proposed approach:

- Prefer Streamlit primitives (`st.container(border=True)`, headings, etc.) for background/text.
- Where custom HTML/CSS is necessary (drag-and-drop backlog list), use Streamlit / browser theme variables when available and provide sensible fallbacks.
  - Example: use `color: var(--text-color, #111); background: var(--secondary-background-color, #f7f7f7)` rather than fixed dark-only palettes.

## Risks / Trade-offs

- Streamlit DOM structure and CSS variables can change between Streamlit versions; sticky behavior and theme-variable usage may require small adjustments.
- Adding `search_query` to `ListFilters` changes a core dataclass API; tests and call sites must be updated.

## Migration Plan

- Add the new page file without changing the current default planner.
- Add search filtering capability and update list rendering to pass the query.
- Add unit tests for search behavior.

## Open Questions

- Confirm whether “Backlog sticks” should be:
  - (A) sticky to browser viewport while the page scrolls (assumed), or
  - (B) sticky within a scrollable list container (if we implement the list as its own scroll region).
