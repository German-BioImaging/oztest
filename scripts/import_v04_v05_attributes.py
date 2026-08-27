#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Import v0.4/v0.5 parse_attributes cases from the `ngff` repo's 0.4/0.5
submodule suite JSON files into oztest's per-file case layout.

Source: <ngff-repo>/specifications/{0.4,0.5}/tests/*_suite.json
Dest:   cases/parse_attributes/v{0.4,0.5}/{core,strict}/{valid,invalid}/{kind}/<name>.json

Each suite test's "data" field is written out as the dest file content, with
keys sorted alphabetically to match the `pretty-format-json` pre-commit hook
(prek.toml) -- avoids annoying diffs if running the script multiple times.

Usage:
    uv run scripts/import_v04_v05_attributes.py /path/to/ngff
"""

import argparse
import json
from pathlib import Path

DEST_ROOT = Path(__file__).resolve().parent.parent / "cases" / "parse_attributes"

SUITE_KIND = {
    "image_suite.json": "image",
    "label_suite.json": "label",
    "plate_suite.json": "plate",
    "well_suite.json": "well",
    "strict_image_suite.json": "image",
    "strict_label_suite.json": "label",
    "strict_plate_suite.json": "plate",
    "strict_well_suite.json": "well",
}


def profile_for(suite_filename: str) -> str:
    return "strict" if suite_filename.startswith("strict_") else "core"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ngff_repo",
        type=Path,
        help="Path to a local clone of the `ngff` repo (with 0.4/0.5 submodules checked out)",
    )
    args = parser.parse_args()
    ngff_root = args.ngff_repo / "specifications"

    for version in ("0.4", "0.5"):
        tests_dir = ngff_root / version / "tests"
        seen_names: dict[tuple[str, str, str, str], set[str]] = {}

        for suite_path in sorted(tests_dir.glob("*_suite.json")):
            kind = SUITE_KIND[suite_path.name]
            profile = profile_for(suite_path.name)
            suite = json.loads(suite_path.read_text())

            for test in suite["tests"]:
                validity = "valid" if test["valid"] else "invalid"
                name = Path(test["formerly"]).name
                if not name.endswith(".json"):
                    name += ".json"

                key = (version, profile, validity, kind)
                used = seen_names.setdefault(key, set())
                # one duplicate test in the suites (plate/duplicate_rows)
                # name the second with a 2
                if name in used:
                    stem, ext = name.rsplit(".", 1)
                    n = 2
                    while f"{stem}-{n}.{ext}" in used:
                        n += 1
                    name = f"{stem}-{n}.{ext}"
                used.add(name)

                dest_dir = DEST_ROOT / f"v{version}" / profile / validity / kind
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / name
                dest_path.write_text(
                    json.dumps(test["data"], indent=2, sort_keys=True) + "\n"
                )

        print(f"v{version}: wrote {sum(len(v) for v in seen_names.values())} files")


if __name__ == "__main__":
    main()
