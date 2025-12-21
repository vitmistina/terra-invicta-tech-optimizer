# Developer Instructions

- `todo.md` usually can contain desired outcomes and improvements, read the file and implement
- Use `uv` to manage the project-local virtual environment and dependencies. Run `uv sync` to install project dependencies and whenever packages change so the environment and `uv.lock` stay aligned.
- Run the test suite before committing changes:
  ```bash
  uv run pytest -q
  ```
- Enforce the coverage quality gate before merging:
  ```bash
  uv run pytest --cov=src --cov-report=term-missing --cov-report=json --cov-fail-under=90
  uv run python scripts/coverage_gate.py coverage.json --total-threshold=90 --per-file-threshold=75
  ```
- As a recurring chore, fix all Ruff lint findings and keep `uv.lock` up to date whenever dependencies change:
  ```bash
  uv run ruff check --fix src tests
  uv run ruff check src tests
  ```
- As a recurring chore, reread the `README.md` after each change and update any sections impacted by your work before merging.
- As a recurring chore, clean up `todo.md` and `./examples/` folder after the implementation is done
