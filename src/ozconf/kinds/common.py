from __future__ import annotations

import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Literal, NamedTuple

from ..case_filter import Case

JSON = int | float | str | None | list["JSON"] | dict[str, "JSON"]
Status = Literal["pass", "fail", "error", "skip"]

logger = logging.getLogger(__name__)


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
    """Class describing the information returned by a dingus."""

    case: Case
    invocation: list[str]
    return_code: int
    output: JSON | None
    stderr: str | None


@dataclass
class OutputConfig:
    out_file: Path | None
    format: Literal["tsv", "json"]

    def is_a_tty(self) -> bool:
        return self.out_file is None and sys.stdout.isatty()

    @contextmanager
    def open(self) -> Generator[IO[str]]:
        if self.out_file is None:
            yield sys.stdout
            return

        if self.out_file.exists():
            logger.warning("Overwriting output file %s", self.out_file)

        with open(self.out_file, "w") as f:
            yield f
