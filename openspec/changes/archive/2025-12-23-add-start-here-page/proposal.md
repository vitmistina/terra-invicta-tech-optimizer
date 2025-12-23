# Change: Add “Start here” page (wireframe-based)

## Why

The current Streamlit app’s entrypoint (`main.py`) already provides the core planner workflow, but it lacks the wireframe-aligned “Start here” layout and a dedicated Friendly Name search. A “Start here” page improves onboarding by presenting the planner workspace in a clearly structured layout (filters + sticky backlog + long list), while keeping the UI legible in both Streamlit light and dark themes.

## What Changes

- Add a new Streamlit multipage entry named **Start here** that implements the layout from `docs/start-here.drawio.svg`.
- Make **Start here** the default landing page when the app is launched.
- Reuse existing planner components from `main.py` where possible (filters, backlog, list rendering, model caching).
- Add a **Search** input that filters the technology/project list by **Friendly Name only** (case-insensitive substring match).
- Debounce Search updates so filtering starts only after a short idle delay (fast typing, fewer reruns).
- Ensure the “Backlog” panel **sticks to the top of the browser window** as the user scrolls through long technology lists.
- Ensure the Start here page remains high-contrast / readable in both **light** and **dark** Streamlit themes.
- Minimize custom CSS: prefer Streamlit native components and default styling; use only small, scoped CSS where required (e.g., sticky backlog / existing drag-and-drop backlog).

## Impact

- Affected UI files:
  - `pages/Start_here.py` (new)
  - `main.py` (shared logic updates; search/filter plumbing; theme-safe styling)
- Affected core logic (likely):
  - `terra_invicta_tech_optimizer/planner_data.py` (extend list filtering to support Friendly Name search efficiently)
- Tests:
  - `tests/test_planner_data.py` (add coverage for Friendly Name-only search)

## Compatibility / Migration

- No expected breaking changes for existing users.
- The existing planner entrypoint in `main.py` will redirect to Start here so the default landing page matches the wireframe.

## Open Questions

- None.
