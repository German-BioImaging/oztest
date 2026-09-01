#!/usr/bin/env python3
"""Script to create a new zarr node."""

from __future__ import annotations

import json
import logging
import sys
from argparse import ArgumentParser
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from shutil import rmtree
from typing import TypeVar

logger = logging.getLogger("mknode")

T = TypeVar("T")

JSON = float | int | str | None | bool | list["JSON"] | dict[str, "JSON"]
JSONObject = dict[str, "JSON"]
METADATA_FILE = "zarr.json"
DATA_TYPES = ["bool"]
for base in ("int", "uint"):
    for precision in (8, 16, 32, 64):
        DATA_TYPES.append(f"{base}{precision}")
for precision in (32, 64):
    DATA_TYPES.append(f"float{precision}")
for precision in (64, 128):
    DATA_TYPES.append(f"complex{precision}")


def parse_list(string: str, fn: Callable[[str], T], sep: str = ",") -> list[T]:
    return [fn(s.strip()) for s in string.split(sep)]


def list_parser(fn: Callable[[str], T], sep: str = ",") -> Callable[[str], list[T]]:
    return partial(parse_list, fn=fn, sep=sep)


def jso(s: str) -> JSONObject:
    j = json.loads(s)
    if not isinstance(j, dict):
        raise TypeError(f"Expected JSON object, got {s}")
    return j


@dataclass
class ArrayArgs:
    shape: list[int]
    data_type: str
    fill_value: JSON

    @property
    def chunk_shape(self) -> list[int]:
        return self.shape.copy()

    @classmethod
    def maybe_from_args(
        cls,
        shape: list[int] | None,
        data_type: str | None,
        fill_value: JSON | None = None,
    ):
        if shape is None and data_type is None:
            return None
        if (shape is None) != (data_type is None):
            raise ValueError("All array args must be given or none")
        if fill_value is None:
            if data_type == "bool":
                fill_value = False
            else:
                fill_value = 0
        return cls(shape, data_type, fill_value)  # type:ignore

    def get_metadata(self, attributes: JSONObject | None = None) -> JSONObject:
        if attributes is None:
            attributes = {}

        a2b: JSONObject = {"name": "bytes"}
        if self.data_type not in ("bool", "int8", "uint8"):
            a2b["configuration"] = {"endian": "little"}

        d = {
            "zarr_format": 3,
            "node_type": "array",
            "shape": self.shape,
            "data_type": self.data_type,
            "chunk_grid": {
                "name": "regular",
                "configuration": {"chunk_shape": self.shape},
            },
            "chunk_key_encoding": {"name": "default"},
            "fill_value": self.fill_value,
            "codecs": [a2b],
            "attributes": attributes,
        }
        return d


@dataclass
class Args:
    path: Path
    store: Path | None
    attributes: JSONObject
    force: bool
    parents: bool
    log_level: int
    array_args: ArrayArgs | None

    def __post_init__(self):
        if (
            self.store is not None
            and self.store != self.path
            and self.store not in self.path.parents
        ):
            raise ValueError("store must be an ancestor of path")

    @classmethod
    def parse(cls, raw_args: list[str] | None = None):
        parser = ArgumentParser(description=__doc__)
        parser.add_argument("path", type=Path, help="file system path to new node")
        parser.add_argument(
            "--store",
            "-s",
            type=Path,
            help="file system path to store root, which must be an ancestor of the `path` argument; if not given, defaults to the nearest ancestor with the extension .ome.zarr",
        )
        parser.add_argument(
            "-a",
            "--attributes",
            type=jso,
            help="attributes to add to the new node, as a JSON string representing an object",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            default=False,
            help="if the node already exists, delete it",
        )
        parser.add_argument(
            "-p",
            "--parents",
            action="store_true",
            default=False,
            help="create parent Zarr groups, including the store root and its parent directory, if necessary",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="increase logging verbosity",
        )
        g = parser.add_argument_group(
            "array", "Additional arguments for creating an array rather than a group."
        )
        g.add_argument(
            "shape",
            type=list_parser(int),
            nargs="?",
            help="comma-separated list of unsigned integers representing array shape",
        )
        g.add_argument(
            "datatype",
            nargs="?",
            choices=DATA_TYPES,
            help="data type for the array",
        )
        g.add_argument(
            "--fill-value",
            "-F",
            type=jso,
            help="JSON string representing fill value to be used; not type-checked",
        )
        parsed = parser.parse_args(raw_args)
        maybe_array = ArrayArgs.maybe_from_args(
            parsed.shape, parsed.datatype, parsed.fill_value
        )
        level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(
            parsed.verbose, logging.DEBUG
        )
        storepath: Path | None = parsed.store
        nodepath: Path = parsed.path
        if storepath is None:
            if nodepath.name.endswith(".ome.zarr"):
                storepath = nodepath
            else:
                for p in nodepath.parents:
                    if p.name.endswith(".ome.zarr"):
                        storepath = p
                        break

        return cls(
            nodepath,
            storepath,
            parsed.attributes or {},
            parsed.force,
            parsed.parents,
            level,
            maybe_array,
        )


def eprint(*args, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    print(*args, **kwargs)


def grp_metadata(attrs: JSONObject | None = None) -> JSONObject:
    if attrs is None:
        attrs = {}
    return {"zarr_format": 3, "node_type": "group", "attributes": attrs}


def write_node_metadata(path: Path, metadata: JSONObject):
    s = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    p = path.joinpath(METADATA_FILE)
    p.write_text(s)
    if logger.isEnabledFor(logging.INFO):
        logger.info(
            "Wrote metadata into %s : %s", p, json.dumps(metadata, sort_keys=True)
        )


def write_group_metadata(path: Path, attrs: JSONObject | None = None):
    write_node_metadata(path, grp_metadata(attrs))


def main():
    args = Args.parse()
    logging.basicConfig(level=args.log_level)

    if args.store is not None:
        if not args.store.name.endswith(".ome.zarr"):
            logger.warning("Store path should end with .ome.zarr")

        if args.store != args.path:
            args.store.mkdir(exist_ok=True, parents=args.parents)

    nodepath = args.path
    if nodepath.exists():
        if args.force:
            logger.warning("Removing existing node at %s", nodepath)
            rmtree(nodepath)
        else:
            eprint(f"Node already exists at {nodepath} ; use --force to overwrite")
            return 1
    nodepath.mkdir(parents=args.parents)
    if args.array_args is None:
        write_group_metadata(nodepath, args.attributes)
    else:
        meta = args.array_args.get_metadata(args.attributes)
        write_node_metadata(nodepath, meta)

    if args.store is None:
        logger.warning(
            "No --store given, and could not infer from .ome.zarr extension; parent group metadata will not be written"
        )
    else:
        while nodepath != args.store:
            nodepath = nodepath.parent
            if not nodepath.joinpath(METADATA_FILE).exists():
                write_group_metadata(nodepath)
    return 0


if __name__ == "__main__":
    status = main()
    sys.exit(status)
