# Change: Move Start Here list toward category dataframes

## Why
The Start Here page renders ~1000 rows with per-row widgets, causing significant perceived latency. Moving to category-level dataframes with centralized backlog actions can reduce widget density while preserving usability.

## What Changes
- Update Start Here requirements to allow a category-based dataframe/table presentation.
- Preserve category icons and backlog-add workflows while reducing per-row widgets.

## Impact
- Affected specs: planner-start-here
- Affected code: pages/Start_here.py, streamlit_app/ui/start_page.py, shared UI helpers (future implementation)
