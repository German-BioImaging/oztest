from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import Awaitable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import IO, Literal, NamedTuple, Protocol, Self, TypeAlias, cast

from rich import print as rprint
from rich.progress import Progress, TaskID

from oztest.types import JSON, Status

from ..case_filter import Case, CaseFilter

logger = logging.getLogger(__name__)


def format_status(s: Status) -> str:
    fmt = None
    match s:
        case "pass":
            fmt = "green"
        case "skip" | "xfail":
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
class Oztest:
    description: str | None = None

    @classmethod
    def from_path(cls, p: Path) -> Self | None:
        if p.is_dir():
            p = p.joinpath("oztest.json")
        if not p.exists():
            return None
        txt = p.read_text()
        jso = json.loads(txt)
        return cls.from_jso(jso)

    @classmethod
    def from_jso(cls, jso: JSON) -> Self:
        if not isinstance(jso, dict):
            raise TypeError(f"Expected JSON object, got {type(jso).__name__}")
        return cls(cast(str, jso.get("description")))


OutputFormat: TypeAlias = Literal["tsv", "json"]


@dataclass
class OutputConfig:
    out_file: Path | None
    format: OutputFormat
    progress: Progress

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


async def read_stream(stream: None | asyncio.StreamReader) -> str | None:
    if stream is None:
        logger.debug("No output")
        return None
    b = await stream.read()
    return b.decode()


async def read_json(stream: None | asyncio.StreamReader, logger=logger) -> JSON | None:
    s = await read_stream(stream)
    if not s:
        return s
    logger.debug("Got raw output: %s", s)
    return json.loads(s)


@dataclass
class ValidationResult:
    case: Case
    invocation: list[str]
    status: Status
    message: str | None

    @classmethod
    def field_names(cls, full=True) -> list[str]:
        out = ["slug"]
        if full:
            out.extend(
                [
                    "kind",
                    "oz_version",
                    "profile",
                    "expected_validity",
                    "name",
                ]
            )
        out.extend(["result", "message"])
        return out

    def to_dict(self, full=True, color=False) -> dict[str, str]:
        d = {"slug": self.case.slug()}
        if full:
            d.update(
                {
                    "kind": self.case.kind,
                    "oz_version": str(self.case.version),
                    "profile": self.case.profile,
                    "expected_validity": self.case.validity,
                    "name": self.case.name,
                }
            )

        if color:
            d["result"] = format_status(self.status)
        else:
            d["result"] = self.status

        if self.message is not None:
            d["message"] = self.message
        return d


class Runner(Protocol):
    def __call__(
        self, dingus: list[str], case: Case, prog_task: tuple[Progress, TaskID]
    ) -> Awaitable[ValidationResult]: ...


async def run_cases(
    dingus: list[str],
    cases: CaseFilter,
    output: OutputConfig,
    runner: Runner,
):
    futs: list[Awaitable[ValidationResult]] = []
    prog = output.progress
    gath_task = prog.add_task("Gathering cases", total=None)
    exec_task = prog.add_task("Running tests", total=None, start=False)
    for tcase, should_run in cases:
        if not should_run:
            continue
        futs.append(runner(dingus, tcase, (prog, exec_task)))
        prog.advance(gath_task)
    prog.stop_task(gath_task)
    prog.update(exec_task, total=len(futs))
    prog.start_task(exec_task)
    results = await asyncio.gather(*futs)
    prog.stop_task(exec_task)

    match output.format:
        case "json":
            jso = {
                "command": dingus,
                "oztest_version": version("oztest"),
                "results": [v.to_dict(True, False) for v in results],
            }
            with output.open() as f:
                json.dump(jso, f, indent=2, sort_keys=True)
        case "tsv":
            with output.open() as f:
                delim = "\t"
                field_names = ValidationResult.field_names(False)
                # Can't use csv.DictWriter here because we may need to use `rich.print` to color status output.
                rprint(delim.join(field_names), file=f)
                for v in results:
                    d = v.to_dict(False, output.is_a_tty())
                    rprint(delim.join(d.get(n, "") for n in field_names), file=f)
        case s:
            raise RuntimeError(f"Unknown output format '{s}'")
