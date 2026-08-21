import asyncio
import json
import logging
import subprocess as sp
from collections.abc import Awaitable
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any, Self

from rich import print as rprint

from ..case_filter import Case, CaseFilter
from ..types import Validity
from .common import JSON, OutputConfig, Status, format_status

logger = logging.getLogger(__name__)


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


async def run_parse_attributes_single(dingus: list[str], case: Case):
    logger = logging.getLogger(f"{__name__}.{case.slug()}")
    with case.as_path() as p:
        cmd = [*dingus, str(p)]
        logger.debug("Running command: %s", cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=sp.PIPE, stderr=sp.PIPE
        )
        return_code = await proc.wait()

        res, _stderr = await asyncio.gather(
            read_json(proc.stdout, logger), read_stream(proc.stderr)
        )

    status: Status | None = None
    msg: str | None = None
    if return_code != 0:
        status = "error"

    if res:
        output = Output.from_jso(res)  # type: ignore
        if output.validity == case.validity:
            status = status or "pass"
        elif output.xfail:
            status = status or "xfail"
        else:
            status = status or "fail"
    else:
        status = "error"
        msg = "No output from dingus"

    return ValidationResult(case, cmd, status, msg)


@dataclass
class ValidationResult:
    case: Case
    invocation: list[str]
    status: Status
    message: str | None

    @classmethod
    def field_names(cls, full=True) -> list[str]:
        out = []
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
        out.extend(["slug", "result", "message"])
        return out

    def to_dict(self, full=True, color=False) -> dict[str, str]:
        d = {}
        if full:
            d.update(
                {
                    "kind": self.case.kind,
                    "oz_version": self.case.version.raw,
                    "profile": self.case.profile,
                    "expected_validity": self.case.validity,
                    "name": self.case.name,
                }
            )

        d["slug"] = self.case.slug()

        if color:
            d["result"] = format_status(self.status)
        else:
            d["result"] = self.status

        if self.message is not None:
            d["message"] = self.message
        return d


@dataclass
class Output:
    validity: Validity
    message: str | None = None
    xfail: bool = False

    @classmethod
    def from_jso(cls, d: dict[str, Any]) -> Self:
        v = d.get("validity")
        if v not in ("valid", "invalid"):
            raise ValueError(f'"validity" must be "valid" or "invalid"; got {v!r}')
        msg = d.get("message")
        if msg is not None and not isinstance(msg, str):
            raise TypeError(f'"message" must be a string; got {msg!r}')
        xfail = d.get("xfail", False)
        if not isinstance(xfail, bool):
            raise TypeError(f'"xfail" must be boolean, got {xfail!r}')

        return cls(v, msg, xfail)


async def run_parse_attributes(
    dingus: list[str], cases: CaseFilter, output: OutputConfig
):
    futs: list[Awaitable[ValidationResult]] = []
    for tcase, should_run in cases:
        if not should_run:
            continue
        futs.append(run_parse_attributes_single(dingus, tcase))

    out = await asyncio.gather(*futs)

    match output.format:
        case "json":
            results = [v.to_dict(True, False) for v in out]
            jso = {
                "command": dingus,
                "ozconf_version": version("ozconf"),
                "results": results,
            }
            with output.open() as f:
                json.dump(jso, f, indent=2, sort_keys=True)
        case "tsv":
            with output.open() as f:
                delim = "\t"
                field_names = ValidationResult.field_names(False)
                # Can't use csv.DictWriter here because we may need to use `rich.print` to color status output.
                rprint(delim.join(field_names), file=f)
                for v in out:
                    d = v.to_dict(False, output.is_a_tty())
                    rprint(delim.join(d.get(n, "") for n in field_names), file=f)
        case s:
            raise RuntimeError(f"Unknown output format '{s}'")
