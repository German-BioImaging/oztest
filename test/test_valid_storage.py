import json

import pytest

from oztest.case_filter import Case, CaseFilter


def parametrize_cases(filt: CaseFilter):
    cases = sorted(c for c, _ in filt)
    argnames = ("case",)
    argvalues: list[tuple[Case]] = []
    ids: list[str] = []
    for c in cases:
        argvalues.append((c,))
        ids.append(c.slug())

    def decorator(test_fn):
        return pytest.mark.parametrize(argnames, argvalues, ids=ids)(test_fn)

    return decorator


@parametrize_cases(CaseFilter.from_args(kinds=["parse_attributes"]))
def test_attributes_are_json(case: Case):
    """Test that the attribute tests are all valid JSON."""
    with case.as_path() as p:
        assert p.is_file()
        text = p.read_text()
        json.loads(text)


@parametrize_cases(
    CaseFilter.from_args(kinds=["validate_zarr", "transform_coordinates"])
)
def test_zarr_tests_are_zarr(case: Case):
    pytest.importorskip("zarr")
    import zarr

    with case.as_path() as p:
        root = zarr.open(p, mode="r")

        if isinstance(root, zarr.Group):
            for _ in root.members(None):
                pass
