from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, Self

Kind = Literal["parse_attributes", "transform_coordinates", "validate_zarr"]
Validity = Literal["valid", "invalid"]
JSON = int | float | str | None | Sequence["JSON"] | Mapping[str, "JSON"]
Status = Literal["pass", "fail", "error", "skip", "xfail"]


def parse_dingus_invocation(items: list[str] | None) -> None | list[str]:
    if items is None:
        return None

    if items[0] == "--":
        items.pop(0)

    return items if items else None


class FromJso(Protocol):
    @classmethod
    def from_jso(cls, jso: JSON) -> Self: ...
