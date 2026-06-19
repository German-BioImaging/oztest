from typing import Literal

Kind = Literal["parse_attributes", "transform_coordinates", "validate_zarr"]


def parse_dingus_invocation(items: list[str] | None) -> None | list[str]:
    if items is None:
        return None

    if items[0] == "--":
        items.pop(0)

    return items if items else None
