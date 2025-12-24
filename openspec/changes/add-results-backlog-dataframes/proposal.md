# Change: Add backlog dataframes to Results page

## Why
Users need visibility into the raw backlog order and the prerequisite-expanded backlog to understand the research path computed on the Results page.

## What Changes
- Display a dataframe that repeats backlog items in their current order.
- Display an "exploded" backlog dataframe that includes all prerequisite technologies needed for the backlog.
- Document how duplicates and researched items are handled during backlog explosion.

## Impact
- Affected specs: planner-results (new)
- Affected code: pages/Results.py, terra_invicta_tech_optimizer graph/backlog helpers (as needed)
