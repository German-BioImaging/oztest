_:
    just --list

pre-commit-install:
    uv run --group dev prek install

# Manually run all pre-commit hooks.
pre-commit:
    uv run --group dev prek run --all-files

# Lint and type check the python package.
lint:
    uv run --group dev ruff check src test
    uv run --group dev mypy src test
    uv run --group dev ruff format --check src test

# Fix lint and formatting issues in the python package.
fix:
    uv run --group dev ruff check --fix src test
    uv run --group dev ruff format src test

# Start a python REPL with all dependencies installed.
repl:
    uv run --all-groups --all-extras --with ipython ipython

# Test the python package.
test:
    uv run --no-default-groups --no-dev --group test pytest -v
