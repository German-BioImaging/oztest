import typer
from pathlib import Path
import shutil
from importlib.resources import files, as_file

app = typer.Typer(no_args_is_help=True)


@app.command()
def export(path: Path):
    """Export the test cases to a given directory."""
    path.mkdir(exist_ok=True, parents=True)
    for item in path.iterdir():
        raise FileExistsError(f"Target directory {path} is not empty")

    for item in files("ozconf.cases").iterdir():
        if item.name.startswith("__") or item.name.startswith("."):
            continue
        with as_file(item) as d:
            shutil.copytree(d, path / d.name)


@app.command()
def hello():
    print("Hello, world!")


if __name__ == "__main__":
    app()
