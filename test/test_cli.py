import logging
import subprocess as sp
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)


def oztest(*args: str) -> str:
    if args is None:
        args = []

    res = sp.run(["oztest", *args], check=False, capture_output=True, text=True)
    assert res.returncode == 0
    stdout = res.stdout.rstrip()
    logger.info("Called oztest %s :: got\n%s", args, stdout)
    return stdout


def test_help():
    out = oztest("--help")
    assert "Usage:" in out


def test_version():
    ver = oztest("version")
    assert ver.startswith("oztest v")


def test_export(tmp_path: Path):
    outdir = tmp_path / "outdir"
    oztest("export", str(outdir))
    assert outdir.is_dir()
    # TODO: once we have test cases, check that they're dumped here


@pytest.mark.parametrize(
    ("item",), [("kind",), ("version",), ("validity",), ("name",), ("slug",)]
)
def test_query_kind(item: str):
    oztest("query", item)


@pytest.mark.parametrize(
    ("kind",), [("parse_attributes",), ("transform_coordinates",), ("validate_zarr",)]
)
def test_find_parse_attributes(kind: str):
    oztest("find", kind)
