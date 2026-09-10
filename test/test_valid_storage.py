import json
from typing import Any

import pytest

from oztest.case_filter import Case, CaseFilter


def _cases_as_parametrize_kwargs(
    filt: CaseFilter,
) -> tuple[tuple[str, ...], list[tuple], dict[str, Any]]:
    cases = sorted(c for c, _ in filt)
    argnames = ("case",)
    argvalues = [(c,) for c in cases]
    kwargs = {"ids": [c.slug() for c in cases]}
    return (argnames, argvalues, kwargs)


def parametrize_cases(filt: CaseFilter):
    argnames, argvalues, kwargs = _cases_as_parametrize_kwargs(filt)

    def decorator(test_fn):
        return pytest.mark.parametrize(argnames, argvalues, **kwargs)(test_fn)

    return decorator


@parametrize_cases(CaseFilter.from_args(kinds=["parse_attributes"]))
def test_attributes_are_json(case: Case):
    """Test that the attribute tests are all valid JSON."""
    with case.as_path() as p:
        assert p.is_file()
        text = p.read_text()
        json.loads(text)


@parametrize_cases(
    CaseFilter.from_args(
        kinds=["validate_zarr", "transform_coordinates"], version_spec=">=0.5"
    )
)
def test_zarr_tests_are_zarr(case: Case):
    zarrista = pytest.importorskip("zarrista")
    with case.as_path() as p:
        assert p.is_dir()
        store = zarrista.store.FilesystemStore(p)
        root = zarrista.Group.open(store)
        # not sure whether this will error for malformed nodes,
        # or just skip
        _ = root.traverse()
