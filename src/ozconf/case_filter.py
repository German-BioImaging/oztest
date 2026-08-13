from collections.abc import Callable, Generator, Iterable, Iterator
from contextlib import contextmanager
from functools import total_ordering
from pathlib import Path
import re
import os
from typing import Any
import logging
import fnmatch

from importlib.resources import files, as_file
from packaging.version import Version
from packaging.specifiers import SpecifierSet

logger = logging.getLogger(__name__)


def case_kinds(path: Path | None = None) -> Iterable[tuple[str, Any]]:
    """Iterate over case kinds and the associated Traversable."""
    if path is None:
        path = files("ozconf.cases")  # type: ignore
    for item in path.iterdir():  # type: ignore
        if item.name.startswith("__") or item.name.startswith(".") or not item.is_dir():
            continue
        yield (item.name, item)


def case_kind_versions(case_kind_trav) -> Iterable[tuple[Version, Any]]:
    """Given a case kind Traversable, iterate over the contained versions and their associated Traversable."""
    for d in case_kind_trav.iterdir():
        if d.name.startswith("v") and d.is_dir():
            ver = OzVersion(d.name)
            yield (ver, d)


def case_kind_version_profiles(case_kind_version_trav) -> Iterable[tuple[str, Any]]:
    for d in case_kind_version_trav.iterdir():
        if d.is_dir():
            yield (d.name, d)


def case_kind_version_profile_validities(
    case_kind_version_profile_trav,
) -> Iterable[tuple[str, Any]]:
    """Given a case kind version Traversable, iterate over the contained validities and their associated Traversable."""
    for d in case_kind_version_profile_trav.iterdir():
        if d.is_dir():
            yield (d.name, d)


def _iter_files_recursive(trav, prefix: str = "") -> Iterable[tuple[str, Any]]:
    """Recursively walk a Traversable, yielding (relative_path, Traversable) for every file found.

    Test cases may be nested arbitrarily deeply under `validity`
    (e.g. `invalid/image/foo.json`) purely for organisational purposes;
    that nesting is not itself a filterable attribute.
    """
    for item in trav.iterdir():
        if item.name.startswith("__") or item.name.startswith("."):
            continue
        rel = f"{prefix}/{item.name}" if prefix else item.name
        if item.is_dir():
            yield from _iter_files_recursive(item, rel)
        else:
            yield (rel, item)


def case_kind_version_validity_names(
    case_kind_version_validity_trav,
) -> Iterable[tuple[str, Any]]:
    """Given a case kind version validity Traversable, recursively iterate over all
    contained test case files (at any depth) and their associated Traversable.
    The name yielded is the path relative to `validity`, minus extension."""
    for rel, item in _iter_files_recursive(case_kind_version_validity_trav):
        name, _, ext = rel.rpartition(".")
        yield (name if ext else rel, item)


class OzVersion(Version):
    def __init__(self, version: str) -> None:
        if not version.startswith("v"):
            raise ValueError("Version expected to start with 'v'")
        self.raw = version
        super().__init__(version)


@total_ordering
class Case:
    """Information about a test case.

    Use `Case.as_path` as a context manager to get a path to the real location of the test case.
    """

    def __init__(
        self,
        traversable,
        kind: str,
        version: "OzVersion",
        profile: str,
        validity: str,
        name: str,
    ) -> None:
        """Takes a Traversable as from `importlib.resources.files`, plus the explicit
        kind/version/profile/validity/name context.

        This context cannot be reliably inferred from `traversable`'s path alone,
        since cases may be nested arbitrarily deeply under `validity`.
        """
        self.kind = kind
        self.version = version
        self.profile = profile
        self.validity = validity
        self.name = name

        self.traversable = traversable

    def __eq__(self, value: object) -> bool:
        return isinstance(value, type(self)) and self.traversable == value.traversable

    def __le__(self, rhs: object) -> bool:
        if not isinstance(rhs, type(self)):
            return NotImplemented
        if self.kind < rhs.kind:
            return True
        if self.version < rhs.version:
            return True
        if self.profile < rhs.profile:
            return True
        if self.validity < rhs.validity:
            return True
        if self.name < rhs.name:
            return True
        return False

    @contextmanager
    def as_path(self) -> Generator[Path]:
        """Get the accessible path of the test case."""
        if isinstance(self.traversable, os.PathLike):
            yield Path(self.traversable)
        else:
            with as_file(self.traversable) as p:
                yield p

    def slug(self) -> str:
        """Get the full identifier of the test case."""
        return "/".join(
            [self.kind, self.version.raw, self.profile, self.validity, self.name]
        )

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.slug()})"


def make_version_filter(
    specifier: str | None = None,
) -> Callable[[Version], bool] | None:
    if specifier is None:
        return None
    sset = SpecifierSet(specifier)

    def fn(ver: Version) -> bool:
        return sset.contains(ver)

    return fn


def make_kind_filter(include: Iterable[str] | None) -> Callable[[str], bool] | None:
    if include is None:
        return None

    include = {i.lower() for i in include}

    def fn(kind: str) -> bool:
        return kind.lower() in include

    return fn


def make_validity_filter(
    include: Iterable[str] | None = None, exclude: Iterable[str] | None = None
) -> Callable[[str], bool] | None:
    """
    Multiple expressions are combined with OR.
    Excludes override includes.
    """
    if include is None and exclude is None:
        return None

    include_set = None if include is None else {s.lower() for s in include}
    exclude_set = None if exclude is None else {s.lower() for s in exclude}

    def fn(validity: str) -> bool:
        v = validity.lower()
        if include_set is not None and v not in include_set:
            return False
        if exclude_set is not None and v in exclude_set:
            return False
        return True

    return fn


def is_fnmatch(s: str):
    return not set("*?[]").isdisjoint(s)


def str_to_re(s: str):
    if s.startswith("/"):
        pat = s[1:]
    elif is_fnmatch(s):
        pat = fnmatch.translate(s)
    else:
        pat = f".*{s}.*"
    return re.compile(pat)


def make_str_filter(
    include: Iterable[str] | None = None,
    exclude: Iterable[str] | None = None,
) -> Callable[[str], bool] | None:
    """Include and exclude patterns can be:

    - plain strings: treated as a substring which could occur anywhere in the name
    - fnmatch: if the special characters `*`, `?`, `[`, or `]` occur in the pattern,
      treat it as a unix-style filename pattern match
    - regular expression: if the string starts with `/`, treat the remainder as a regular expression

    Multiple expressions are combined with OR.
    Excludes override includes.
    """
    if include is None and exclude is None:
        return None
    includes = None if include is None else [str_to_re(s) for s in include]
    excludes = None if exclude is None else [str_to_re(s) for s in exclude]

    def fn(s: str) -> bool:
        if includes is not None and not any(r.match(s) for r in includes):
            return False
        if excludes is not None and any(r.match(s) for r in excludes):
            return False
        return True

    return fn


class CaseFilter(Iterable):
    """Iterates over a set of tests and whether they should be run."""

    def __init__(
        self,
        additional_cases: list[Path] | None = None,
        builtin_cases: bool = True,
        kind_filter: Callable[[str], bool] | None = None,
        version_filter: Callable[[Version], bool] | None = None,
        profile_filter: Callable[[str], bool] | None = None,
        validity_filter: Callable[[str], bool] | None = None,
        name_filter: Callable[[str], bool] | None = None,
        verbose: bool = False,
    ):
        """Takes filters for various test features.

        If None, the filter accepts all cases.
        Otherwise, only accepts cases where the callable returns True.

        If `verbose` is False (default), only tests which should be run are yielded.
        """
        self.logger = logging.getLogger(f"{__name__}.{type(self).__name__}")

        self.kind_filter = kind_filter
        self.version_filter = version_filter
        self.profile_filter = profile_filter
        self.validity_filter = validity_filter
        self.name_filter = name_filter

        self.additional_cases = additional_cases or []
        self.builtin_cases = builtin_cases
        self.verbose = verbose

    def _iter_case_roots(self) -> Iterator[tuple[Case, bool]]:
        if self.builtin_cases:
            yield from self._iter_kinds()
        for root in self.additional_cases:
            yield from self._iter_kinds(root)

    def _iter_kinds(self, root: Path | None = None) -> Iterator[tuple[Case, bool]]:
        for kind, kpath in case_kinds(root):
            kind_run = True
            if self.kind_filter is not None and not self.kind_filter(kind):
                kind_run = False
                self.logger.debug("Filtered out kind '%s'", kind)
                if not self.verbose:
                    continue
            yield from self._iter_versions(kpath, kind_run, kind)

    def _iter_versions(
        self, kind_trav, run: bool, kind: str
    ) -> Iterator[tuple[Case, bool]]:
        for version, verpath in case_kind_versions(kind_trav):
            ver_run = run
            if (
                ver_run
                and self.version_filter is not None
                and not self.version_filter(version)
            ):
                self.logger.debug("Filtered out version '%s'", version)
                ver_run = False
                if not self.verbose:
                    continue
            yield from self._iter_profiles(verpath, ver_run, kind, version)

    def _iter_profiles(
        self, version_trav, run: bool, kind: str, version: OzVersion
    ) -> Iterator[tuple[Case, bool]]:
        for profile, propath in case_kind_version_profiles(version_trav):
            pro_run = run
            if (
                pro_run
                and self.profile_filter is not None
                and not self.profile_filter(profile)
            ):
                self.logger.debug("Filtered out profile '%s'", profile)
                pro_run = False
                if not self.verbose:
                    continue
            yield from self._iter_validities(propath, pro_run, kind, version, profile)

    def _iter_validities(
        self, profile_trav, run: bool, kind: str, version: OzVersion, profile: str
    ) -> Iterator[tuple[Case, bool]]:
        for validity, valpath in case_kind_version_profile_validities(profile_trav):
            val_run = run
            if (
                val_run
                and self.validity_filter is not None
                and not self.validity_filter(validity)
            ):
                self.logger.debug("Filtered out validity '%s'", validity)
                val_run = False
                if not self.verbose:
                    continue
            yield from self._iter_names(
                valpath, val_run, kind, version, profile, validity
            )

    def _iter_names(
        self,
        validity_trav,
        run: bool,
        kind: str,
        version: OzVersion,
        profile: str,
        validity: str,
    ) -> Iterator[tuple[Case, bool]]:
        for name, npath in case_kind_version_validity_names(validity_trav):
            this_run = run
            if run and self.name_filter is not None and not self.name_filter(name):
                self.logger.debug("Filtered out name '%s', validity")
                this_run = False
                if not self.verbose:
                    continue

            case = Case(npath, kind, version, profile, validity, name)
            if this_run:
                self.logger.debug("Selected test case '%s'", case.slug())
            yield case, this_run

    def __iter__(self) -> Iterator[tuple[Case, bool]]:
        yield from self._iter_case_roots()
