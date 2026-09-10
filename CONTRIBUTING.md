# Contributing

Use the Python version in `.python-version` and install the locked project and
development dependencies:

```bash
uv sync --locked
```

Before committing, run the same checks as CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
```

Apply mechanical formatting with `uv run ruff format .`. Ruff keeps the
repository's 100-character line length and import-order policy from
`pyproject.toml`.

`scripts/refresh_all.py` runs both Ruff checks before the test suite and feed
builds. `--skip-tests` skips pytest only; it does not bypass lint or formatting.
This keeps every Backend release on the same baseline enforced by CI.
