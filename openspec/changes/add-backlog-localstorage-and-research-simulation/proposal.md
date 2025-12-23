# Proposal: add-backlog-localstorage-and-research-simulation

## Background
- The Streamlit planner currently keeps backlog state in-session only. Users want the Start here backlog to persist between browser sessions without re-entering priorities.
- User stories US-07, US-09, and US-10 in `docs/user_stories.md` outline simulation and visualization expectations, but the document predates the Start here workflow and needs refreshed specs.

## Goals
- Specify backlog persistence in browser `localStorage`, including load-on-open and continuous synchronization from Streamlit state.
- Capture updated requirements for research slot simulation, category mix visualization, and slot utilization timelines aligned with the Start here experience.
- Mark the legacy user stories document as superseded by the new specs once implemented.

## Non-goals
- Implementing the features (spec-only change).
- Altering other user stories beyond US-07/09/10.

## Proposed Work
- Add a backlog persistence capability spec covering localStorage load/save behaviors and resilience.
- Add a research simulation and timeline spec that modernizes US-07/09/10 around the current planner/backlog workflows.
- Provide a task list to drive implementation and deprecate the old `docs/user_stories.md` coverage for these items.
