import logging
import subprocess as sp
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)


def ozconf(*args: str) -> str:
    if args is None:
        args = []

    res = sp.run(["ozconf", *args], check=False, capture_output=True, text=True)
    assert res.returncode == 0
    stdout = res.stdout.rstrip()
    logger.info("Called ozconf %s :: got\n%s", args, stdout)
    return stdout


def test_help():
    out = ozconf("--help")
    assert "Usage:" in out


def test_version():
    ver = ozconf("version")
    assert ver.startswith("ozconf v")


def test_export(tmp_path: Path):
    outdir = tmp_path / "outdir"
    ozconf("export", str(outdir))
    assert outdir.is_dir()
    # TODO: once we have test cases, check that they're dumped here


@pytest.mark.parametrize(
    ("item",), [("kind",), ("version",), ("validity",), ("name",), ("slug",)]
)
def test_query_kind(item: str):
    ozconf("query", item)


@pytest.mark.parametrize(
    ("kind",), [("parse_attributes",), ("transform_coordinates",), ("validate_zarr",)]
)
def test_find_parse_attributes(kind: str):
    ozconf("find", kind)
