#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "jsonschema",
#     "referencing",
#     "platformdirs",
# ]
# ///
"""
Dingus CLI for testing attribute cases.

Fetches schemas from https://ngff.openmicroscopy.org.
Expected to fail for at least some cases in the "strict" profile,
and "invalid" validity.

Use like `oztest run parse_attributes --include-validity valid --exclude-profile strict --version-filter '===0.4' -- ./scripts/jsonschema_dingus.py 0.4`

Before running for the first time, run ./scripts/jsonschema_dingus.py --build-cache to download all the schemas.
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from argparse import ArgumentParser
from functools import cache
from io import BytesIO, IOBase
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import platformdirs
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

logger = logging.getLogger("jsonschema_dingus")

OME_ZARR_VERSIONS = ("0.4", "0.5", "0.6")
NGFF_ORIGIN = "https://ngff.openmicroscopy.org"
DIRS = platformdirs.PlatformDirs("oztest")


class SchemaCache:
    def __init__(self) -> None:
        self.root = DIRS.user_cache_path.joinpath("jsonschema_dingus")
        self.root.mkdir(parents=True, exist_ok=True)

    def clear(self):
        for entry in self.root.iterdir():
            if entry.is_file():
                entry.unlink()
            else:
                shutil.rmtree(entry)

    def path_for(self, uri: str) -> Path:
        return self.root.joinpath(quote(uri, safe=""))

    def get_bytes(self, uri: str) -> bytes | None:
        p = self.path_for(uri)
        try:
            return p.read_bytes()
        except FileNotFoundError:
            return None

    def extract_schemas(self, zip_readable: IOBase, uri_prefix: str) -> int:
        count = 0
        with zipfile.ZipFile(zip_readable) as z:
            root = zipfile.Path(z)
            container = next(root.iterdir())
            for p in container.joinpath("schemas").iterdir():
                uri = uri_prefix + p.name
                content = p.read_bytes()
                p = self.path_for(uri)
                p.write_bytes(content)
                count += 1
        return count


SCHEMA_CACHE = SchemaCache()


def fetch_bytes(uri: str) -> bytes:
    """Fetch bytes from a web resource."""
    logger.debug("Fetching bytes from %s", uri)
    req = Request(
        uri,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.4129.107"
        },
        method="GET",
    )
    try:
        rsp = urlopen(req)
    except HTTPError:
        logger.error("Could not fetch %s", uri)

    if rsp.status != 200:
        raise RuntimeError(f"Could not fetch {uri}: {rsp.status} {rsp.reason}")
    b = rsp.read()
    return b


def read_bytes(uri: str):
    """Read bytes from the local cache or web."""
    b = SCHEMA_CACHE.get_bytes(uri)
    if b is None:
        raise ValueError(f"No cache entry; use --build-cache : {uri}")
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
                {"$ref": f"{NGFF_ORIGIN}/0.4/schemas/{v}.schema"} for v in variants
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
    uri = f"{NGFF_ORIGIN}/{version}/schemas/ome_zarr.schema"
    registry = Registry(retrieve=retrieve_resource)
    validator = Draft202012Validator({"$ref": uri}, registry=registry)
    return validator


def parse_args(raw_args: list[str] | None):
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "-v", "--verbose", action="count", help="increase logging verbosity"
    )
    parser.add_argument(
        "-c",
        "--build-cache",
        action="store_true",
        help="build the local schema cache",
    )
    parser.add_argument(
        "kind",
        choices=("parse_attributes", "validate_zarr"),
        nargs="?",
        help="test kind; required unless --build-cache is given",
    )
    parser.add_argument(
        "version",
        nargs="?",
        choices=OME_ZARR_VERSIONS,
        help="schema version; required unless --build-cache is given",
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="path to zarr attributes; required unless --build-cache is given",
    )
    return parser.parse_args(raw_args)


def build_cache():
    SCHEMA_CACHE.clear()
    for version in OME_ZARR_VERSIONS:
        zip_uri = f"https://github.com/ome/ngff-spec/archive/refs/heads/{version}.zip"
        rd = BytesIO(fetch_bytes(zip_uri))
        n_schemas = SCHEMA_CACHE.extract_schemas(
            rd, f"{NGFF_ORIGIN}/{version}/schemas/"
        )
        logger.info("Cached %s schemas", n_schemas)


def main(raw_args=None):
    args = parse_args(raw_args)
    log_level = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
    }.get(args.verbose or 0, logging.DEBUG)
    logging.basicConfig(level=log_level)
    if args.build_cache:
        return build_cache()

    validator = make_validator(args.version)
    d = {}
    strpath = str(args.path)
    # I don't really like trying to guess things from the path, but...
    if any(seg in strpath for seg in ["/strict/", "/invalid/"]):
        d["xfail"] = True

    if args.kind == "parse_attributes":
        # parse_attributes test
        attrs = json.loads(args.path.read_bytes())
        try:
            validator.validate(attrs)
            d["validity"] = "valid"
        except ValidationError as e:
            d["validity"] = "invalid"
            d["message"] = str(e)
    elif args.kind == "validate_zarr":
        # validate_zarr or transform_coordinates test
        for root, _dirs, files in args.walk():
            for fname in files:
                if fname == ".zattrs":
                    attrs = json.loads(root.joinpath(fname).read_bytes())
                elif fname == "zarr.json":
                    attrs = json.loads(root.joinpath(fname).read_bytes()).get(
                        "attributes", {}
                    )
                else:
                    continue

                try:
                    validator.validate(attrs)
                    d["validity"] = "valid"
                except ValidationError as e:
                    d["validity"] = "invalid"
                    d["message"] = str(e)
                    break
    else:
        raise ValueError(f"Unsupported test kind '{args.kind}'")

    print(json.dumps(d))


if __name__ == "__main__":
    main()
