# OME-Zarr conformance tests

> ⚠️ This project is a work in progress. The test suites are expected to grow and almost certainly need further correction. ⚠️

This repository provides test cases and testing tools for OME-Zarr implementations.

The cases themselves are organised by type in the `cases/` directory.
See below for a short overview of the test types,
and the README.md files in each directory for further details.
Implementors may incorporate these cases directly into their unit tests.

Additionally, this repository provides a python package which contains all of the test data and CLI tools for using it.
Commonly, OME-Zarr implementors provide a simple ["dingus"](https://talk.commonmark.org/t/origin-of-the-usage-for-dingus/1226) CLI,
whose arguments and intended function are specified in this repository.
The testing tools then invoke the dingus with one test case at a time,
collect the output, and tabulate the implementation's conformance to expectations.

## Test case layout

Test cases are found in the [`cases/`](./cases/) directory.
The path to each test from there is `{kind}/v{version}/{profile}/{validity}/{name}{extension}`.

- Each kind directory has its own README.md, as they are structured differently and likely require different dingus CLIs
- The version corresponds to an OME-Zarr version
- The profile corresponds to whether support for particular tests are required in the core spec, optional, or some extension
- The validity of a test case allows for "expected failure" cases - e.g. where validators _should_ refuse to parse some particular case
- The name of a test is local to the kind/ version/ profile/ validity
- The extension is used to identify whether the test is a JSON file (`.json`), an OME-Zarr hierarchy (`.ome.zarr`), or something else

Tests are globally identified by a slug made up of the above path, minus the extension, e.g. `parse_attributes/v0.5/core/valid/easy_test`.

For ease of navigation, tests can be further organised into arbitrary subdirectories within the `valid/`, `invalid/`
level, e.g. `parse_attributes/v0.5/core/valid/image/easy/easy_test`. These subdirectories are not available
for filtering.

Implementors may supply their own additional test cases.
In order to use them with the `oztest` tool, they MUST be in a comparable directory hierarchy.
Implementation-specific behaviour SHOULD be tested using a `profile` specific to that implementation.

## Using the conformance tester

Install the `oztest` python package using **uv**, pipx, or pip, and invoke it from your terminal with `oztest`.
Alternatively, run it within an ephemeral environment with `uvx oztest` (requires uv).

The tool allows you to

- `export` the built-in test cases from the package distribution
- `query` which of the above attributes are available for a given set of test filters (e.g. which OME-Zarr versions have cases for a particular test kind)
- `find` which tests match a given set of filters
- `test` with the built-in and/or your own cases, using your dingus CLI

## Data validation conformance levels

Conformance for validating OME-Zarr data and metadata can be tested at several levels.

1. Validating that individual fields of a zarr attributes object are valid (cf. JSONSchema).
2. Validating a single zarr attributes object containing OME-Zarr metadata

    - Validates that correct data can be represented, and that internally inconsistent data can be caught
    - Cannot validate references to other objects in the zarr hierarchy
    - Cannot validate conformance to other zarr metadata e.g. array data type, dimensionality

3. Validating a metadata-only zarr hierarchy

    - Can validate references to other objects and other zarr metadata
    - Cannot validate values e.g. the invertibility of an affine matrix defined as a zarr array (but can validate that array's shape and dtype)

4. Validating a zarr hierarchy with data

## Test kinds

### parse_attributes

These cases exercise levels 1 and 2 validation;
whether a single Zarr attributes object containing OME-Zarr can be represented and validated.

See [cases/parse_attributes/README.md](./cases/parse_attributes/README.md) for more details.

### validate_zarr

These cases exercise levels 1-4 validation;
whether an entire Zarr hierarchy containing OME-Zarr data can be represented and validated.

See [cases/validate_zarr/README.md](./cases/validate_zarr/README.md) for more details.

### transform_coordinates

These cases test the numerical accuracy of coordinate transformations (introduced in OME-Zarr v0.6 by RFC-5).

See [cases/transform_coordinates/README.md](./cases/transform_coordinates/README.md) for more details.

## Test case provenance

`parse_attributes/v0.4` and `parse_attributes/v0.5` test cases were imported from their submodules in the `ngff`
repo in [PR #5](https://github.com/clbarnes/oztest/pull/5). The script used for this import is under `scripts/import_v04_v05_attributes.py`.

`parse_attributes/v0.6` and `validate_zarr/v0.6` test cases were imported in [PR #13](https://github.com/clbarnes/oztest/pull/13)
from the `ngff-spec` repo at commit [5c76733](https://github.com/ome/ngff-spec/commit/5c76733fe3a1f97a3957909c879b15d57689f74e).
The script used for this import is under `scripts/import_v06_cases.py`.

## Versioning

This project is currently in alpha (`0.x` series).
The project version does not correspond to OME-Zarr versions: see the [changelog](./CHANGELOG.md) for details on support for different OME-Zarr versions.

Once released, this repository will use [calendar versioning](https://calver.org/) with format `<YYYY>.<MM>.<minor>`
under the [python package version scheme](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-scheme)
originally proposed in [PEP 440](https://peps.python.org/pep-0440/).

## Contributing

This project uses [just](https://github.com/casey/just) for common development tasks.
Once installed, run `just` to see the available recipes.

This project uses [prek](https://prek.j178.dev/) to run pre-commit validation.
Run `just pre-commit-install` to install the hooks.

CLI functionality is tested using [pytest](https://docs.pytest.org/en/stable/).
Run `just test` to run the tests.
