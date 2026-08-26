# Contributing to experiment-server

## Project overview

`experiment-server` is a Python package for defining and serving experiment configurations. It provides:

- A Python API and client API.
- A command-line interface exposed as `experiment-server`.
- An HTTP server for serving participant-specific configurations.
- A Textual terminal UI for managing participants and editing configurations.
- TOML configuration parsing, validation, and JSON generation.

The main package is in `experiment_server/`. Tests are in `test/`. Documentation sources are in `docs/` and the project README contains the primary usage examples.

## Development setup

This project uses Poetry. Install dependencies, including development dependencies, with:

```sh
poetry install
```

Run commands inside the Poetry environment with `poetry run`, or enter it with:

```sh
poetry shell
```

The supported Python range is `>=3.10,<4.0`.

## Validation

Run the test suite with:

```sh
poetry run pytest
```

The pytest configuration in `pyproject.toml` enables coverage, verbose output, and test discovery under `test/`.

Run the configured type checker with:

```sh
poetry run mypy experiment_server
```

Compile-check changed Python files when making a narrow edit:

```sh
poetry run python -m compileall experiment_server/path/to/file.py
```

Before committing, inspect the diff and check for whitespace errors:

```sh
git diff --check
git diff --cached --check
```

Use the project's tests and existing conventions as the source of truth. Do not treat generated files, coverage output, or local temporary configuration files as source changes.

## Common commands

Run the CLI from the repository checkout with:

```sh
poetry run experiment-server --help
poetry run experiment-server verify-config-file sample_config.toml
poetry run experiment-server ui -c sample_config.toml
```

Build the documentation with:

```sh
poetry run mkdocs build
```

## Configuration and data files

Experiment configurations use TOML. `sample_config.toml` is the checked-in example. Validate configuration changes with the CLI or the relevant Python tests. Be careful when editing configuration order, block names, participant indices, and strategy settings because these values affect participant assignment.

Do not commit generated participant JSON, temporary TOML files, coverage output, build output, or local server state unless a task explicitly requires them.

## Implementation notes

- Keep changes focused and preserve the public API unless the task explicitly changes it.
- Prefer the existing standard-library and project dependencies over adding new dependencies.
- Preserve compatibility with Python 3.10 and later supported versions.
- The Textual UI includes both Python code and styles in `experiment_server/static/css/`. Scope CSS selectors carefully so a new rule does not affect unrelated widgets.
- For dependent UI inputs, use peer-aware Textual validators. Handle empty input and intermediate text such as `-` without raising, and validate both visible fields before enabling an action.
- Configuration edits should be validated before loading or saving where the existing workflow supports it.
- Log user-facing operational errors through the project's existing logging conventions rather than printing directly.

## Tests

Add or update tests under `test/` for behavior changes. Prefer focused tests that cover both valid and invalid configuration or participant states. For UI validation changes, cover empty fields, non-numeric intermediate input, invalid ranges, and recovery after correcting the peer field when practical.

Do not modify tests merely to make an implementation pass. If behavior changes intentionally, document the reason in the change and update affected tests and documentation together.
