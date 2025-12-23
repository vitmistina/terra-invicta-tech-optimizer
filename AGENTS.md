<!-- OPENSPEC:START -->

# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Developer Instructions

- `todo.md` usually can contain desired outcomes and improvements, read the file and implement
- Use `uv` to manage the project-local virtual environment and dependencies. Run `uv sync` to install project dependencies and whenever packages change so the environment and `uv.lock` stay aligned.
- Run the test suite before committing changes:
  ```bash
  uv run pytest -q
  ```
- Enforce the coverage quality gate before merging:
  ```bash
  uv run pytest --cov=terra_invicta_tech_optimizer --cov-report=term-missing --cov-report=json --cov-fail-under=90
  uv run python scripts/coverage_gate.py coverage.json --total-threshold=90 --per-file-threshold=75
  ```
- As a recurring chore, fix all Ruff lint findings and keep `uv.lock` up to date whenever dependencies change:
  ```bash
  uv run ruff check --fix terra_invicta_tech_optimizer tests
  uv run ruff check terra_invicta_tech_optimizer tests
  ```
- As a recurring chore, reread the `README.md` after each change and update any sections impacted by your work before merging.
- As a recurring chore, clean up `todo.md` and `./examples/` folder after the implementation is done
