# Attribute-parsing test cases

Test cases in this directory are JSON files representing the attributes of a Zarr node (`.zattrs` in Zarr v2, `zarr.json#/attributes` in Zarr v3).

Within each version subdirectory, cases are organised by the level of support expected in OME-Zarr validators:

- `must`: the case contains valid metadata which MUST be parsed by a minimal implementation of the OME-Zarr specification
- `should`: the case contains valid metadata including some optional, but core, features of the OME-Zarr specification
- `may`: the case contains valid metadata including registered extensions to the OME-Zarr specification
- `must_not`: the case contains metadata which is invalid according to the OME-Zarr specification and should raise an error either when attempting to read or write it

Implementations should parse the attributes and return a non-zero error code if they are invalid according to level 2 validation.
