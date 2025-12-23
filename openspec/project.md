# Project Context

## Purpose

`terra-invicta-tech-optimizer` is a local, interactive planning tool for the game Terra Invicta.

It loads tech + project definitions (a dependency DAG) from files in `inputs/`, validates the graph, then provides a Streamlit UI to:

- Browse techs/projects by category.
- Filter (category/completion/backlog) and curate a prioritized backlog.
- Explore prerequisites/dependents in a graph view.

The repo currently focuses on input ingestion + DAG visualization helpers and a minimal Streamlit “planner/results/graph” workflow.

## Tech Stack

- Language/runtime: Python 3.12 (see `.python-version`, `pyproject.toml`)
- UI: Streamlit multipage app (`main.py`, `pages/Graph.py`, `pages/Results.py`)
- Graph rendering: Streamlit Graphviz integration (`st.graphviz_chart`) + `graphviz` Python package
- Dependency management: `uv` (`uv.lock` is committed)
- Tests: `pytest` (tests live in `tests/`)

## Project Conventions

### Code Style

- Prefer typed, small functions and dataclasses for data containers.
  - Most modules use `from __future__ import annotations`.
  - Data models are `@dataclass` (e.g., `Node`, `GraphView` and view DTOs).
- Naming:
  - Modules/functions/variables: `snake_case`
  - Classes/enums: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- Paths/filesystem:
  - Use `pathlib.Path` (not raw strings) for filesystem locations.
- Ordering/determinism:
  - Input files are processed in sorted order.
  - UI option lists are sorted for stability.

Formatting/linting:

- The repo references Ruff in `AGENTS.md` / user stories, but there is no Ruff config file checked in yet.
- If Ruff is introduced, prefer repository-wide defaults plus the smallest config necessary.

### Architecture Patterns

This repository has two layers:

1. **Core package** (`terra_invicta_tech_optimizer/`)

   - Pure-ish logic for parsing, validation, and graph “view model” preparation.
   - Key types:
     - `Node` and `NodeType` in `terra_invicta_tech_optimizer/input_loader.py`
     - `GraphExplorer` + `GraphFilters` + view DTOs in `terra_invicta_tech_optimizer/graph.py`
     - `GraphValidator` + `ValidationResult` in `terra_invicta_tech_optimizer/validation.py`

2. **Streamlit app** (`main.py` + `pages/`)
   - UI composition, session state, caching, and rendering.
   - Uses `st.session_state` as the single source of truth for:
     - `filters`, `backlog`, `completed`, `selected`, `reload_token`
   - Uses `st.cache_data` to cache input loading keyed by a reload token.

UI patterns (Streamlit):

- “Planner” in `main.py` is the entrypoint.
- “Graph” and “Results” are separate multipage files under `pages/` that import shared helpers from `main.py`.
- Graph rendering is done by building a DOT string and passing it to `st.graphviz_chart`.
- The backlog drag-and-drop uses an embedded HTML component (`streamlit.components.v1`).

### Testing Strategy

- Use `pytest` unit tests with small in-memory graphs and `tmp_path` fixtures.
- Tests target the core package:
  - Input parsing: supported file types, node typing, warnings/errors.
  - Graph view building: highlighting, filtering, caching.
  - Graph validation rules.

Notes:

- Tests live in `tests/` and import the package via `tests/conftest.py` adding the repo root to `sys.path`.
- If you add/modify behavior, prefer adding a focused unit test first (or alongside) in `tests/`.

### Git Workflow

- No strict workflow is enforced in-repo.
- Suggested default:
  - Short-lived feature branches
  - PRs/merge to main
  - Keep commits scoped and descriptive (one logical change per commit)

## Domain Context

Terra Invicta represents research as a dependency graph of:

- **Techs**: researchable technologies.
- **Projects**: follow-on research items (often unlocked by tech).

Domain concepts in this repo:

- Each node has a stable identifier (`dataName`, `id`, or `name`) and a friendly display name (`friendlyName`).
- Nodes may have a category (`techCategory`) and arbitrary metadata (e.g., `researchCost`).
- Dependencies are expressed as prerequisites (`prereqs` / `dependencies`) and form a DAG.
- The app uses the dependency graph for:
  - Validation gating (block planning if the DAG is invalid).
  - Graph exploration (highlight prerequisite chains and dependents).
  - Filtering (category/completion/backlog).

## Important Constraints

- Runs locally as a Streamlit app; no backend service.
- Input loading should be resilient:
  - Supported formats: JSON/CSV/TSV.
  - Unknown/unsupported files in `inputs/` are ignored with warnings.
- Graph validation must protect users from planning on invalid data (cycles/missing references).
- Performance should remain acceptable for large graphs:
  - Prefer caching (see `GraphExplorer` view cache + `st.cache_data`).
  - Avoid repeated full recomputation in UI code when inputs are unchanged.

## External Dependencies

- Terra Invicta data exports/templates (user-supplied files in `inputs/`)
- Streamlit
- Graphviz (via Streamlit + `graphviz` package)

There are no network services or external APIs integrated at this time.
