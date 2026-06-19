default:
    just --list

pre-commit:
    uv run --group dev prek run --all-files

lint:
    uv run --group dev ruff check src
    uv run --group dev mypy src
    uv run --group dev ruff format --check src

fix:
    uv run --group dev ruff check --fix src
    uv run --group dev ruff format src

repl:
    uv run --all-groups --all-extras --with ipython ipython
