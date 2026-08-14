default:
    just --list

pre-commit:
    uv run --group dev prek run --all-files

lint:
    uv run --group dev ruff check src test
    uv run --group dev mypy src test
    uv run --group dev ruff format --check src test

fix:
    uv run --group dev ruff check --fix src test
    uv run --group dev ruff format src test

repl:
    uv run --all-groups --all-extras --with ipython ipython

test:
    uv run --no-default-groups --no-dev --group test pytest -v
