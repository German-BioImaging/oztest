# Attribute-parsing test cases

Test cases in this directory are JSON files representing the attributes of a Zarr node (`.zattrs` in Zarr v2, `zarr.json#/attributes` in Zarr v3).

## Dingus

The dingus should be a shell command which takes as its last argument the path to a local file.

It should

- Read the file
- Parse it as a JSON-serialised object representing the attributes of a Zarr node
- Extract any fields associated with OME-Zarr, and determine whether the metadata document is internally valid
- Print a JSON-serialised object to standard output
- Exit with a return code of 0

Nonzero exit codes will be reported with status `error`.

### Response object

| key | required | type | description |
| --- | -------- | ---- | ----------- |
| `"validity"` | yes | `"valid"` or `"invalid"` | Validity of the metadata document |
| `"xfail"` | no, default `false` | boolean | Whether a failure should be reported with status `xfail` instead of `fail`. |
| `"message"` | no | string | Free text to be reported. |
