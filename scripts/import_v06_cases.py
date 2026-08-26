#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Import v0.6 parse_attributes and validate_zarr cases from the `ngff-spec`
repo's unversioned `spec`/`strict` test fixtures.

Pin your local `ngff-spec` clone to the
appropriate tag (e.g. `0.6rc0`) before running this script.

Source: <ngff-spec-repo>/tests/attributes/{spec,strict}/**/*.json
        <ngff-spec-repo>/tests/zarr/{spec,strict}/**/*.ome.zarr/zarr.json
Dest:   cases/parse_attributes/v0.6/{core,strict}/{valid,invalid}/{kind}/<name>.json
        cases/validate_zarr/v0.6/{core,strict}/{valid,invalid}/{kind}/<name>.ome.zarr/zarr.json

Usage:
    uv run scripts/import_v06_cases.py /path/to/ngff-spec
"""

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROFILE_MAP = {"spec": "core", "strict": "strict"}


def normalize(data: dict) -> dict:
    """Drop the `_conformance` key and any pre-release suffix e.g. rc0 used in the source fixtures."""
    # handle both zarr.json and direct attribute test cases
    container = data.get("attributes", data)
    container.pop("_conformance", None)
    if "ome" in container:
        # this module only ever imports v0.6 cases, so we can hardcode the version here
        container["ome"]["version"] = "0.6"
    return data


def copy_tree(src_root: Path, dest_root: Path, glob_pattern: str) -> int:
    count = 0
    for src_profile, dest_profile in PROFILE_MAP.items():
        profile_root = src_root / src_profile
        for src_path in sorted(profile_root.rglob(glob_pattern)):
            rel = src_path.relative_to(profile_root)
            dest_path = dest_root / dest_profile / rel

            data = normalize(json.loads(src_path.read_text()))
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ngff_spec_repo",
        type=Path,
        help="Path to a local clone of `ngff-spec`, checked out at the appropriate tag (e.g. `0.6rc0`)",
    )
    args = parser.parse_args()

    n_attrs = copy_tree(
        args.ngff_spec_repo / "tests" / "attributes",
        REPO_ROOT / "cases" / "parse_attributes" / "v0.6",
        "*.json",
    )
    print(f"parse_attributes: wrote {n_attrs} files")

    n_zarr = copy_tree(
        args.ngff_spec_repo / "tests" / "zarr",
        REPO_ROOT / "cases" / "validate_zarr" / "v0.6",
        "zarr.json",
    )
    print(f"validate_zarr: wrote {n_zarr} files")


if __name__ == "__main__":
    main()
