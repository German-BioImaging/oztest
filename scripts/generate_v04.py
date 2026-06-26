#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["ozconf"]
#
# [tool.uv.sources]
# ozconf = { path = "..", editable = true }
# ///
"""Dev tool: generate draft v0.4 `validate_zarr` cases from the existing v0.4 `parse_attributes` ones.

OME-Zarr v0.4 used Zarr v2, so a hierarchy root contains two files:
- `.zgroup`: `{"zarr_format": 2}`
- `.zattrs`: the OME-Zarr attributes directly (no `ome` wrapper, unlike v0.5+)

Each `parse_attributes` case is already a JSON file containing the attributes
object, so the conversion is a direct lift: read the JSON, write `.zgroup` and
`.zattrs` into a new `.ome.zarr/` directory.

This is a draft generator, not a faithful migration tool: review its output
before committing it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from rich import print

from ozconf.case_filter import Case, CaseFilter, make_kind_filter

ZGROUP = {"zarr_format": 2}


def generate_case(case: Case, output_root: Path) -> tuple[str, str]:
    """Returns (status, message) where status is 'ok' or 'error'."""
    with case.as_path() as src:
        try:
            attrs = json.loads(src.read_text())
        except OSError as e:
            return "error", f"couldn't read {src}: {e}"

    dest_dir = output_root / case.profile / case.validity / f"{case.name}.ome.zarr"
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir()

    (dest_dir / ".zgroup").write_text(json.dumps(ZGROUP, indent=2) + "\n")
    (dest_dir / ".zattrs").write_text(json.dumps(attrs, indent=2) + "\n")

    return "ok", str(dest_dir)


def run_generate(cases: CaseFilter, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    colour = {"ok": "green", "error": "red"}
    for case, should_run in cases:
        if not should_run or case.version.raw != "v0.4":
            continue
        status, msg = generate_case(case, output_root)
        print(
            case.slug(), f"[{colour[status]}]{status}[/{colour[status]}]", msg, sep="\t"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_root",
        type=Path,
        nargs="?",
        default=Path(__file__).parent.parent / "cases" / "validate_zarr" / "v0.4",
        help="directory to write draft v0.4 cases into (default: cases/validate_zarr/v0.4)",
    )
    args = parser.parse_args()

    cases = CaseFilter(kind_filter=make_kind_filter(["parse_attributes"]))
    run_generate(cases, args.output_root)
