import asyncio
import logging
import subprocess as sp
from dataclasses import dataclass

from rich.progress import Progress, TaskID

from ..case_filter import Case, CaseFilter
from ..types import Validity
from .common import (
    JSON,
    OutputConfig,
    Status,
    ValidationResult,
    read_json,
    read_stream,
    run_cases,
)

logger = logging.getLogger(__name__)


async def run_parse_attributes_single(
    dingus: list[str], case: Case, prog_task: tuple[Progress, TaskID]
):
    logger = logging.getLogger(f"{__name__}.{case.slug()}")
    with case.as_path() as p:
        cmd = [*dingus, str(p)]
        logger.debug("Running command: %s", cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=sp.PIPE, stderr=sp.PIPE
        )
        return_code = await proc.wait()

        res, stderr = await asyncio.gather(
            read_json(proc.stdout, logger), read_stream(proc.stderr)
        )
        if stderr:
            logger.info("Got STDERR\n%s", stderr)

    status: Status | None = None
    msg: str | None = None
    if return_code != 0:
        status = "error"

    if res:
        output = Output.from_jso(res)
        if output.validity == case.validity:
            status = status or "pass"
        elif output.xfail:
            status = status or "xfail"
        else:
            status = status or "fail"
    else:
        status = "error"
        msg = "No output from dingus"

    prog, task = prog_task
    prog.advance(task)

    return ValidationResult(case, cmd, status, msg)


@dataclass
class Output:
    validity: Validity
    message: str | None = None
    xfail: bool = False

    @classmethod
    def from_jso(cls, d: JSON):
        if not isinstance(d, dict):
            raise TypeError(f"Expected JSON object, got {type(d).__name__}")
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
    await run_cases(dingus, cases, output, run_parse_attributes_single)
