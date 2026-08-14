from __future__ import annotations

from typing import Literal, NamedTuple

from ..case_filter import Case

JSON = int | float | str | None | list["JSON"] | dict[str, "JSON"]
Status = Literal["pass", "fail", "error", "skip"]


def format_status(s: Status) -> str:
    fmt = None
    match s:
        case "pass":
            fmt = "green"
        case "skip":
            fmt = "yellow"
        case "fail":
            fmt = "red"
        case "error":
            fmt = "magenta"

    if fmt is None:
        return s

    return f"[{fmt}]{s}[/{fmt}]"


class Result(NamedTuple):
    case: Case
    invocation: list[str]
    return_code: int
    output: JSON | None
    stderr: str | None
