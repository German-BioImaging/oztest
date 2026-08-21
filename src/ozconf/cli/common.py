import logging
from pathlib import Path
from typing import Annotated, Literal

import typer

from ..types import Validity

QUERY_MSG = """\n
Query may be an exact substring;
or a UNIX-style filename matcher if it has the special characters `*`, `?`, `[`, `]`;
or a regular expression if it starts with `/`.
""".rstrip()
STDIO_PATH = Path("-")

VerbosityArg = Annotated[
    int, typer.Option("--verbose", "-v", count=True, help="Increase logging verbosity.")
]
CustomCasesArg = Annotated[
    list[Path] | None,
    typer.Option("--custom-cases", "-c", help="Root directory for additional cases."),
]
InvokeDingusArgs = Annotated[
    list[str] | None, typer.Argument(help="Dingus CLI invocation.")
]
NoBuiltinArg = Annotated[
    bool, typer.Option("--no-builtin", "-B", help="Skip builtin test cases.")
]
IncludeProfileArgs = Annotated[
    list[str] | None,
    typer.Option(
        "--include-profile",
        "-p",
        help=f"Include only profiles matching this query.{QUERY_MSG}",
    ),
]
ExcludeProfileArgs = Annotated[
    list[str] | None,
    typer.Option(
        "--exclude-profile",
        "-P",
        help=f"Exclude profiles matching this query.{QUERY_MSG}",
    ),
]
IncludeValidityArgs = Annotated[
    list[Validity] | None,
    typer.Option(
        "--include-validity",
        "-a",
        help="Include only validities matching this string. Must match validity exactly.",
    ),
]
ExcludeValidityArgs = Annotated[
    list[Validity] | None,
    typer.Option(
        "--exclude-validity",
        "-A",
        help="Exclude validities matching this string. Must match validity exactly.",
    ),
]
IncludeNameArgs = Annotated[
    list[str] | None,
    typer.Option(
        "--include-name",
        "-n",
        help=f"Include only names matching this query.{QUERY_MSG}",
    ),
]
ExcludeNameArgs = Annotated[
    list[str] | None,
    typer.Option(
        "--exclude-name", "-N", help=f"Exclude names matching this query.{QUERY_MSG}"
    ),
]
KindsArg = Annotated[
    list[str] | None,
    typer.Option(
        "--kind",
        "-k",
        help="Include only tests of this kind. Must match the kind exactly.",
    ),
]
VersionSpecifierArg = Annotated[
    str | None,
    typer.Option(
        "--version-filter",
        "-e",
        help="Select tests for specific OME-Zarr versions with a PEP 440 version range specifier.",
    ),
]
PathOrStdOutputArg = Annotated[
    Path,
    typer.Option(
        "--out-file",
        "-o",
        help="Path to output file, or - for STDOUT.",
    ),
]
FormatArg = Annotated[
    Literal["tsv", "json"],
    typer.Option(
        "--format",
        "-f",
        help="Output format.",
    ),
]


def parse_dingus_invocation(items: list[str] | None) -> None | list[str]:
    if items is None:
        return None

    if items[0] == "--":
        items.pop(0)

    return items if items else None


def setup_logging(verbosity: int):
    lvl = {
        0: logging.ERROR,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
    }.get(verbosity, logging.NOTSET)
    logging.basicConfig(level=lvl)
