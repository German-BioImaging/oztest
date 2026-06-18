# OME-Zarr conformance tests

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

## Types of test

### parse_attributes

These cases test levels 1 and 2 validation;
whether a single Zarr attributes object containing OME-Zarr can be represented and validated.

See [cases/parse_attributes/README.md](./cases/parse_attributes/README.md) for more details.

### validate_zarr

These cases test levels 1-4 validation;
whether an entire Zarr hierarchy containing OME-Zarr data can be represented and validated.

See [cases/validate_zarr/README.md](./cases/validate_zarr/README.md) for more details.

### transform_coordinates

These cases test the numerical accuracy of coordinate transformations (introduced in OME-Zarr v0.6 by RFC-5).

See [cases/transform_coordinates/README.md](./cases/transform_coordinates/README.md) for more details.

## Versioning

This repository uses [calendar versioning](https://calver.org/)
under the [python version scheme](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-scheme)
originally proposed in [PEP 440](https://peps.python.org/pep-0440/).

See the [changelog](./CHANGELOG.md) for details on support for different OME-Zarr versions.
