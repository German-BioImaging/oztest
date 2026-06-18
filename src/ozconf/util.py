from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager
from functools import total_ordering
from pathlib import Path
from typing import Any

from importlib.resources import files, as_file
from parver import Version


def case_kinds() -> Iterable[tuple[str, Any]]:
    for item in files("ozconf.cases").iterdir():
        if item.name.startswith("__") or item.name.startswith("."):
            continue
        yield (item.name, item)


def case_kind_versions(case_kind_trav) -> Iterable[tuple[Version, Any]]:
    for d in case_kind_trav.iterdir():
        if d.name.startswith("v") and d.is_dir():
            ver = Version.parse(d.name[1:])
            yield (ver, d)


def case_kind_version_validities(case_kind_version_trav) -> Iterable[tuple[str, Any]]:
    for d in case_kind_version_trav.iterdir():
        if d.is_dir():
            yield (d.name, d)


def case_kind_version_validity_names(
    case_kind_version_validity_trav,
) -> Iterable[tuple[str, Any]]:
    for d in case_kind_version_validity_trav.iterdir():
        n = d.name.split(".")[0]
        yield (n, d)


@total_ordering
class Case:
    def __init__(self, traversable) -> None:
        self.name = traversable.name.split(".")[0]
        parents = self.traversable.parents
        self.validity: str = next(parents).name
        self.version: Version = Version.parse(next(parents).name[1:])
        self.kind: str = next(parents).name

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
        if self.validity < rhs.validity:
            return True
        if self.name < rhs.name:
            return True
        return False

    @contextmanager
    def as_path(self) -> Generator[Path]:
        with as_file(self.traversable) as p:
            yield p

    def key(self) -> str:
        parts = list(self.traversable.parts[-4:-1])
        parts.append(self.name)
        return "/".join(parts)


class CaseFilter:
    def __init__(
        self,
        kind_filter: Callable[[str], bool] | None = None,
        version_filter: Callable[[Version], bool] | None = None,
        validity_filter: Callable[[str], bool] | None = None,
        name_filter: Callable[[str], bool] | None = None,
    ) -> None:
        self.kind_filter = kind_filter
        self.validity_filter = validity_filter
        self.version_filter = version_filter
        self.name_filter = name_filter

    def __iter__(self) -> Iterable[Case]:
        for kind, kpath in case_kinds():
            if self.kind_filter is not None and not self.kind_filter(kind):
                continue
            for version, verpath in case_kind_versions(kpath):
                if self.version_filter is not None and not self.version_filter(version):
                    continue
                for validity, valpath in case_kind_version_validities(verpath):
                    if self.validity_filter is not None and not self.validity_filter(
                        validity
                    ):
                        continue
                    for name, npath in case_kind_version_validity_names(valpath):
                        if self.name_filter is not None and not self.name_filter(name):
                            continue
                        yield Case(npath)
