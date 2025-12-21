# terra-invicta-tech-optimizer
This project loads tech tree template file from the Terra Invicta game and lets the player browse techs and projects, filter them, and curate a backlog of priorities before running results.

## Streamlit planning workspace

Launch the interactive planner from the repository root:

```bash
uv run streamlit run main.py
```

The main planner provides:

- A validation gate that surfaces missing references, cycles, or project dependency gaps before any planning continues.
- Category and completion filters that can either hide or de-emphasize list items, plus a quick reset back to the full list.
- A combined tech and project list grouped by category, ordered by cost or friendly name, with click-to-add backlog entries.
- A drag-and-drop backlog queue and a "Proceed with calculation" button that opens the Results page.

The Results page provides:

- A landing spot for calculation output (and a shortcut to the Graph page).

The Graph page provides:

- The graph explorer that highlights prerequisites and dependents for the focused node.
- Backlog, completion, and filter tools that influence graph highlighting.

## Input loading and validation

The loader reads tech and project definitions from the `inputs/` directory. Supported formats are JSON, CSV, and TSV. Unsupported files are skipped with warnings so you can keep scratch files alongside the inputs without breaking the loader.

Parsing rules:

- Each record must provide a unique `dataName` (or `id`/`name`) value. `friendlyName` and `techCategory` are captured when present.
- Records are tagged as projects if either the filename includes `project`, the record declares `type=project`, or it contains an `AI_projectRole` field; otherwise they default to techs.
- Dependencies can be provided as a list or a comma-separated string in a `prereqs`/`dependencies` field.

Validation rules applied on load:

- Missing references are reported when a prerequisite is not defined anywhere in the inputs.
- Cycles in the dependency graph are blocked and surfaced with the involved node IDs.
- Projects must depend on at least one tech node.

## Graph exploration and filtering helpers

The `GraphExplorer` utility in `terra_invicta_tech_optimizer/graph.py` prepares DAG data for interactive visualization. It:

- Styles nodes based on type and category so techs and projects render distinctly.
- Builds highlighted prerequisite/dependent chains when a node is selected for contextual focus.
- Applies category, completion, and backlog filters that can either hide or de-emphasize nodes and edges.
- Provides resettable filter defaults for returning to the full graph view.

See `tests/test_graph_explorer.py` for examples of how to assemble a filtered graph view.

## Planning
Detailed user stories and acceptance criteria for the Streamlit app live in [docs/user_stories.md](docs/user_stories.md).
