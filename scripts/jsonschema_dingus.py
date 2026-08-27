#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "jsonschema",
#     "referencing",
# ]
# ///
"""
Dingus CLI for testing attribute cases.

Fetches schemas from https://ngff.openmicroscopy.org.
Expected to fail for at least some cases in the "strict" profile,
and "invalid" validity.

Use like `oztest run parse_attributes --include-validity valid --exclude-profile strict --version-filter '===0.4' -- ./scripts/jsonschema_dingus.py 0.4`
"""

from __future__ import annotations

import json
import logging
import tempfile
from argparse import ArgumentParser
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

logger = logging.getLogger("jsonschema_dingus")

SCHEMA = "https://json-schema.org/draft/2020-12/schema"
OME_ZARR_VERSIONS = ("0.4", "0.5")


class TempFactory:
    def __init__(self) -> None:
        self.root = Path(tempfile.gettempdir()).joinpath("oztest", "jsonschema_dingus")
        self.root.mkdir(parents=True, exist_ok=True)
        self.refresh = False

    def path_for(self, uri: str) -> Path:
        return self.root.joinpath(quote(uri, safe=""))


TEMP_FACTORY = TempFactory()


def fetch_bytes(uri: str):
    """Fetch bytes from a web resource."""
    logger.debug("Fetching schema from %s", uri)
    req = Request(
        uri,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.4129.107"
        },
        method="GET",
    )
    rsp = urlopen(req)
    if rsp.status != 200:
        raise RuntimeError(f"Could not fetch schema: {rsp.status} {rsp.reason}")
    b = rsp.read()
    return b


def read_bytes(uri: str):
    """Read bytes from the local cache or web."""
    p = TEMP_FACTORY.path_for(uri)
    if not TEMP_FACTORY.refresh:
        try:
            b = p.read_bytes()
            logger.debug("Read cache at %s", p)
            return b
        except FileNotFoundError:
            logger.debug("No cache at %s", p)

    b = fetch_bytes(uri)

    # atomicity, probably not necessary
    part = p.with_name(p.name + ".part")
    part.write_bytes(b)
    part.rename(p)
    return b


# Registry probably handles caching but it doesn't hurt
@cache
def retrieve_resource(uri: str):
    b = read_bytes(uri)
    j = json.loads(b)
    res = Resource.from_contents(j)
    return res


def make_validator_04():
    registry = Registry(retrieve=retrieve_resource)
    variants = ["bf2raw", "image", "label", "ome", "plate", "well"]
    validator = Draft202012Validator(
        {
            "anyOf": [
                {"$ref": f"https://ngff.openmicroscopy.org/0.4/schemas/{v}.schema"}
                for v in variants
            ]
        },
        registry=registry,
    )
    return validator


def make_validator(version: str):
    if version == "0.4":
        return make_validator_04()
    elif version not in OME_ZARR_VERSIONS:
        raise NotImplementedError(
            f"Unknown OME-Zarr version '{version}', expected one of {OME_ZARR_VERSIONS}"
        )
    elif version == "0.6":
        version = "dev"
    uri = f"https://ngff.openmicroscopy.org/{version}/schemas/ome_zarr.schema"
    registry = Registry(retrieve=retrieve_resource)
    validator = Draft202012Validator({"$ref": uri}, registry=registry)
    return validator


def parse_args(raw_args: list[str] | None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "-v", "--verbose", action="count", help="increase logging verbosity"
    )
    parser.add_argument(
        "-r",
        "--refresh-cache",
        action="store_true",
        help="refresh the local schema cache",
    )
    parser.add_argument("version", choices=OME_ZARR_VERSIONS, help="schema version")
    parser.add_argument("path", type=Path, help="path to zarr attributes")
    return parser.parse_args(raw_args)


def main(raw_args=None):
    args = parse_args(raw_args)
    log_level = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
    }.get(args.verbose or 0, logging.DEBUG)
    logging.basicConfig(level=log_level)
    if args.refresh_cache:
        TEMP_FACTORY.refresh = True

    validator = make_validator(args.version)
    attrs = json.loads(args.path.read_bytes())
    d: dict[str, Any]
    try:
        validator.validate(attrs)
        d = {"validity": "valid"}
    except ValidationError as e:
        d = {"validity": "invalid", "message": str(e)}

    p = str(args.path)
    # I don't really like trying to guess things from the path, but...
    if any(seg in p for seg in ["/strict/", "/invalid/"]):
        d["xfail"] = True

    print(json.dumps(d))


if __name__ == "__main__":
    main()
