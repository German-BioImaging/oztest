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
