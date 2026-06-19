import asyncio
import sys
import typer
from typing import Annotated, Literal
from pathlib import Path
import shutil
import logging
from importlib.resources import as_file
from ..case_filter import (
    OzVersion,
    case_kinds,
    CaseFilter,
    make_kind_filter,
    make_str_filter,
    make_validity_filter,
    make_version_filter,
)
from ..types import Kind, parse_dingus_invocation
from .common import (
    CustomCasesArg,
    ExcludeNameArgs,
    ExcludeProfileArgs,
    ExcludeValidityArgs,
    IncludeNameArgs,
    IncludeProfileArgs,
    IncludeValidityArgs,
    KindsArg,
    NoBuiltinArg,
    VersionSpecifierArg,
    setup_logging,
    VerbosityArg,
    InvokeDingusArgs,
)
from ..kinds.parse_attributes import run_parse_attributes

app = typer.Typer(no_args_is_help=True)

logger = logging.getLogger(__name__)


@app.command()
def export(
    path: Path,
    force: bool = False,
    verbosity: VerbosityArg = 0,
):
    """Export built-in test cases to a given directory."""
    setup_logging(verbosity)
    if path.exists():
        if force:
            shutil.rmtree(path)
            path.mkdir()
        else:
            for item in path.iterdir():
                raise FileExistsError(f"Target directory {path} is not empty")
    else:
        path.mkdir(parents=True)

    for _, item in case_kinds():
        with as_file(item) as d:
            shutil.copytree(d, path / d.name)


@app.command()
def query(
    item: Literal["kind", "version", "profile", "validity", "name", "slug"],
    kinds: KindsArg = None,
    custom_cases: CustomCasesArg = None,
    no_builtin: NoBuiltinArg = False,
    version_specifier: VersionSpecifierArg = None,
    include_profile: IncludeProfileArgs = None,
    exclude_profile: ExcludeProfileArgs = None,
    include_validity: IncludeValidityArgs = None,
    exclude_validity: ExcludeValidityArgs = None,
    include_name: IncludeNameArgs = None,
    exclude_name: ExcludeNameArgs = None,
    verbosity: VerbosityArg = 0,
):
    """List which test attributes are available with the given filters."""
    setup_logging(verbosity)
    filt = CaseFilter(
        custom_cases,
        not no_builtin,
        make_kind_filter(kinds),
        make_version_filter(version_specifier),
        make_str_filter(include_profile, exclude_profile),
        make_validity_filter(include_validity, exclude_validity),
        make_str_filter(include_name, exclude_name),
    )
    elems = set()
    for tcase, _ in filt:
        match item:
            case "kind":
                elems.add(tcase.kind)
            case "version":
                elems.add(tcase.version)
            case "profile":
                elems.add(tcase.profile)
            case "validity":
                elems.add(tcase.validity)
            case "name":
                elems.add(tcase.name)
            case "slug":
                elems.add(tcase.slug())
    for elem in sorted(elems):
        if isinstance(elem, OzVersion):
            print(elem.raw)
        else:
            print(elem)


@app.command()
def find(
    kind: Kind,
    custom_cases: CustomCasesArg = None,
    no_builtin: NoBuiltinArg = False,
    version_specifier: VersionSpecifierArg = None,
    include_profile: IncludeProfileArgs = None,
    exclude_profile: ExcludeProfileArgs = None,
    include_validity: IncludeValidityArgs = None,
    exclude_validity: ExcludeValidityArgs = None,
    include_name: IncludeNameArgs = None,
    exclude_name: ExcludeNameArgs = None,
    verbosity: VerbosityArg = 0,
):
    """List tests matching given filters."""
    setup_logging(verbosity)
    filt = CaseFilter(
        custom_cases,
        not no_builtin,
        make_kind_filter([kind]),
        make_version_filter(version_specifier),
        make_str_filter(include_profile, exclude_profile),
        make_validity_filter(include_validity, exclude_validity),
        make_str_filter(include_name, exclude_name),
    )
    for tcase, _ in filt:
        print(tcase.slug())


@app.command()
def test(
    kind: Kind,
    custom_cases: CustomCasesArg = None,
    no_builtin: NoBuiltinArg = False,
    version_specifier: VersionSpecifierArg = None,
    include_profile: IncludeProfileArgs = None,
    exclude_profile: ExcludeProfileArgs = None,
    include_validity: IncludeValidityArgs = None,
    exclude_validity: ExcludeValidityArgs = None,
    include_name: IncludeNameArgs = None,
    exclude_name: ExcludeNameArgs = None,
    verbosity: VerbosityArg = 0,
    dingus: InvokeDingusArgs = None,
):
    """Run tests."""
    setup_logging(verbosity)
    filt = CaseFilter(
        custom_cases,
        not no_builtin,
        make_kind_filter([kind]),
        make_version_filter(version_specifier),
        make_str_filter(include_profile, exclude_profile),
        make_validity_filter(include_validity, exclude_validity),
        make_str_filter(include_name, exclude_name),
    )
    args = parse_dingus_invocation(dingus)
    if args is None:
        print("No dingus given; nothing to do")
        return 0

    asyncio.run(run_parse_attributes(args, filt))


@app.command()
def version(
    short: Annotated[
        bool,
        typer.Option("--short", "-s", help="Show the version string and nothing else."),
    ] = False,
):
    """Get the version of this tool."""
    from importlib.metadata import version as _version

    name = __name__.split(".")[0]
    v = _version(name)
    if not short:
        v = f"{name} v{v}"
    print(v)


@app.command(hidden=True)
def dingus(
    args: InvokeDingusArgs,
    stdout: Annotated[
        str | None,
        int,
        typer.Option("--stdout", "-o", help="Print message to standard output."),
    ] = None,
    stderr: Annotated[
        str | None,
        int,
        typer.Option("--stderr", "-e", help="Print message to standard error."),
    ] = None,
    verbosity: VerbosityArg = 0,
    code: Annotated[
        int, typer.Option("--exit-code", "-c", help="Return the given exit code.")
    ] = 0,
):
    """Internal testing tool."""
    setup_logging(verbosity)
    if args:
        logging.info("Got arguments: %s", args)
    else:
        logging.info("Got no arguments")

    if stdout is not None:
        print(stdout)
    if stderr is not None:
        print(stderr, file=sys.stderr)

    raise typer.Exit(code)
