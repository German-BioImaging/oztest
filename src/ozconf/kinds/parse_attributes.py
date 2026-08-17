import asyncio
import json
import logging
import subprocess as sp
from collections.abc import Awaitable

from rich import print

from ..case_filter import Case, CaseFilter
from .common import JSON, Result, Status, format_status

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

        res, stderr = await asyncio.gather(
            read_json(proc.stdout, logger), read_stream(proc.stderr)
        )

        return Result(case, cmd, return_code, res, stderr)


def parse_output(d: dict[str, JSON]):
    return d.get("validity"), d.get("message")


async def run_parse_attributes(dingus: list[str], cases: CaseFilter):
    futs: list[Awaitable[Result]] = []
    for tcase, should_run in cases:
        if not should_run:
            continue
        futs.append(run_parse_attributes_single(dingus, tcase))

    for fut in futs:
        status: Status | None = None
        msg: str | None = None
        res = await fut
        if res.return_code != 0:
            status = "error"

        if res.output:
            validity, msg = parse_output(res.output)  # type: ignore
            if validity == res.case.validity:
                status = status or "pass"
            else:
                status = status or "fail"
        else:
            status = "error"
            msg = "No output from dingus"

        args = [res.case.slug(), format_status(status)]
        if msg:
            args.append(msg)
        print(*args, sep="\t")
