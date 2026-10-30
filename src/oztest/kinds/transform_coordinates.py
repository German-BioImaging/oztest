from __future__ import annotations

import asyncio
import json
import logging
import subprocess as sp
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Self, cast

import numpy as np
from rich.progress import Progress, TaskID

from oztest.case_filter import Case, CaseFilter

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

CONFIG_NAME = "oztest.json"


def validate_coords(jso: JSON) -> list[list[float]]:
    if not isinstance(jso, Sequence):
        raise TypeError(f"coordinates are {type(jso)}, not a sequence")

    out = []

    length = None
    for idx, c in enumerate(jso):
        if not isinstance(c, Sequence):
            raise TypeError(f"coordinate {idx} is {c}, not a sequence")
        if length is None:
            length = len(c)
        elif len(c) != length:
            raise ValueError(
                f"coordinate {idx} does not have expected length {length}: {c}"
            )
        this = []
        for v in c:
            if v is None:
                this.append(float("nan"))
            elif isinstance(v, int):
                this.append(float(v))
            elif not isinstance(v, float):
                raise TypeError(f"coordinate {idx} is not numeric: {c}")
            else:
                this.append(v)
        out.append(this)

    return out


@dataclass
class OztestTransformCoordinates:
    transform_coordinates: TransformCoordinatesConfig
    description: str | None = None

    @classmethod
    def from_jso(cls, jso: JSON) -> Self:
        if not isinstance(jso, dict):
            raise TypeError(f"Expected JSON object, got {type(jso).__name__}")
        return cls(
            TransformCoordinatesConfig.from_jso(jso["transform_coordinates"]),
            cast(str, jso.get("description")),
        )


@dataclass
class Tolerances:
    relative: float = 1e-5
    absolute: float = 1e-8

    @classmethod
    def from_jso(cls, d: JSON) -> Self:
        if not isinstance(d, dict):
            raise TypeError(f"Expected JSON object, got {type(d).__name__}")
        out = cls()
        out.absolute = cast(float, d.get("absolute", out.absolute))
        out.relative = cast(float, d.get("relative", out.relative))
        return out

    def is_close(self, a, b) -> bool:
        return np.allclose(a, b, self.relative, self.absolute, equal_nan=True)


@dataclass
class TransformCoordinatesConfig:
    source: Terminal
    target: Terminal
    tolerance: Tolerances = field(default_factory=Tolerances)

    @classmethod
    def from_jso(cls, jso: JSON) -> Self:
        if not isinstance(jso, dict):
            raise TypeError(f"Expected JSON object, got {type(jso).__name__}")
        src = Terminal.from_jso(jso["source"])
        tgt = Terminal.from_jso(jso["target"])
        tolerance = Tolerances.from_jso(jso.get("tolerance", {}))
        return cls(src, tgt, tolerance)

    def to_args(self) -> DingusArgs:
        coords = json.dumps(
            self.source.coordinates, allow_nan=False, separators=(",", ":")
        )
        return DingusArgs(self.source.name, self.target.name, coords)

    def check_output(self, output: Output) -> Status:
        if self.tolerance.is_close(self.source.coordinates, output.coordinates):
            return "pass"

        if output.xfail:
            return "xfail"

        return "fail"


class DingusArgs(NamedTuple):
    source: str
    target: str
    in_coords: str


@dataclass
class Output:
    coordinates: list[list[float]]
    message: str | None = None
    xfail: bool = False

    def __post_init__(self):
        self.coordinates = validate_coords(self.coordinates)

    @classmethod
    def from_jso(cls, jso: JSON) -> Self:
        if not isinstance(jso, Mapping):
            raise TypeError("Not a mapping")
        coords = validate_coords(jso["coordinates"])
        return cls(
            coords,
            cast(str | None, jso.get("message")),
            cast(bool, jso.get("xfail", False)),
        )


@dataclass
class Terminal:
    name: str
    coordinates: list[list[float]]

    def __post_init__(self):
        self.coordinates = validate_coords(self.coordinates)

    @classmethod
    def from_jso(cls, jso: JSON) -> Self:
        if not isinstance(jso, dict):
            raise TypeError(f"Expected JSON object, got {type(jso).__name__}")
        return cls(cast(str, jso["name"]), cast(list[list[float]], jso["coordinates"]))


def get_config(p: Path):
    jso = p.joinpath(CONFIG_NAME).read_text()
    return OztestTransformCoordinates.from_jso(jso)


async def run_transform_coordinates_single(
    dingus: list[str], case: Case, prog_task: tuple[Progress, TaskID]
):
    logger = logging.getLogger(__name__).getChild(case.slug())

    with case.as_path() as p:
        config = get_config(p)
        cmd = [*dingus, str(p), *config.transform_coordinates.to_args()]
        logger.debug("Running command: %s", cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=sp.PIPE, stderr=sp.PIPE
        )
        return_code = await proc.wait()
        res, stderr = await asyncio.gather(
            read_json(proc.stdout), read_stream(proc.stderr)
        )
        if stderr:
            logger.info("Got STDERR\n%s", stderr)

    status: Status | None = None
    msg: str | None = None
    if return_code != 0:
        status = "error"

    if res:
        output = Output.from_jso(res)
        status = config.transform_coordinates.check_output(output)
        msg = output.message
    else:
        status = "error"
        msg = "No output from dingus"

    prog, task = prog_task
    prog.advance(task)
    return ValidationResult(case, cmd, status, msg)


async def run_transform_coordinates(
    dingus: list[str], cases: CaseFilter, output: OutputConfig
):
    await run_cases(dingus, cases, output, run_transform_coordinates_single)
