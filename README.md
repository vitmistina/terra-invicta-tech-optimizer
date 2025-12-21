# terra-invicta-tech-optimizer
This project loads tech tree template file from the Terra Invicta game and lets the player select a backlog of priority technologies. It calculates optimum path through the Directed Acyclic Graph and provides stats on distribution amongst tech types.

## Input loading and validation

The CLI in `main.py` loads tech and project definitions from the `inputs/` directory and validates the dependency graph. Supported formats are JSON, CSV, and TSV. Unsupported files are skipped with warnings so you can keep scratch files alongside the inputs without breaking the loader.

Parsing rules:

- Each record must provide a unique `dataName` (or `id`/`name`) value. `friendlyName` and `techCategory` are captured when present.
- Records are tagged as projects if either the filename includes `project`, the record declares `type=project`, or it contains an `AI_projectRole` field; otherwise they default to techs.
- Dependencies can be provided as a list or a comma-separated string in a `prereqs`/`dependencies` field.

Validation rules applied on load:

- Missing references are reported when a prerequisite is not defined anywhere in the inputs.
- Cycles in the dependency graph are blocked and surfaced with the involved node IDs.
- Projects must depend on at least one tech node.

Run the loader and validator locally with:

```bash
uv run python main.py
```

## Planning
Detailed user stories and acceptance criteria for the Streamlit app live in [docs/user_stories.md](docs/user_stories.md).
