import json
import logging
from pathlib import Path
from typing import Any

import zarr
from common import parametrize_cases

from oztest.case_filter import Case, CaseFilter

logger = logging.getLogger(__name__)

TEST_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_ROOT.parent
CASE_ROOT = PROJECT_ROOT / "cases"


def contains_attributes(metadata: dict[str, Any], node: zarr.Array | zarr.Group):
    a = node.attrs
    success = True
    for k, v in metadata.items():
        if a.get(k) != v:
            success = False
            break

    if success:
        return True

    if isinstance(node, zarr.Array):
        return False

    for _, member in sorted(node.members()):
        if contains_attributes(metadata, member):
            return True

    return False


@parametrize_cases(
    CaseFilter.from_args(kinds=["parse_attributes"], exclude_profile=["strict"])
)
def test_parse_attributes_have_validate_zarr_equivalent(case: Case):
    pa_slug = case.slug()
    vz_slug = pa_slug.replace("parse_attributes/", "validate_zarr/")
    vz_path = CASE_ROOT.joinpath(vz_slug + ".ome.zarr")
    assert vz_path.is_dir(), (
        f"parse_attributes case {pa_slug} does not have an equivalent validate_zarr case at {vz_path.relative_to(PROJECT_ROOT)}"
    )

    with case.as_path() as p:
        pa_txt = p.read_text()
        pa_jso = json.loads(pa_txt)

    node = zarr.open(vz_path)
    assert contains_attributes(pa_jso, node), (
        f"validate_zarr case at {vz_path.relative_to(PROJECT_ROOT)} does not share metadata with its source parse_attributes case: {pa_slug}"
    )
