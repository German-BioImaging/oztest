# OME-Zarr hierarchy validation test cases

Test cases in this directory are directories which are OME-Zarr hierarchies.

## Dingus

The dingus should be a shell command which takes as its last argument the path to a local OME-Zarr hierarchy.

It should

- Open the path as a file system store
- Open an OME-Zarr node at the root of that store
- Determine whether that node and any nodes referred to within it are valid
- Print a JSON-serialised object to standard output
- Exit with a return code of 0

Nonzero exit codes will be reported with status `error`.

### Response object

| key | required | type | description |
| --- | -------- | ---- | ----------- |
| `"validity"` | yes | `"valid"` or `"invalid"` | Validity of the metadata document |
| `"xfail"` | no, default `false` | boolean | Whether a failure should be reported with status `xfail` instead of `fail`. |
| `"message"` | no | string | Free text to be reported. |
