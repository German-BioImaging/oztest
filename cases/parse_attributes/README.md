# Attribute-parsing test cases

Test cases in this directory are JSON files representing the attributes of a Zarr node (`.zattrs` in Zarr v2, `zarr.json#/attributes` in Zarr v3).

## Dingus
The "dingus" is a command-line tool that runs the individual test cases for a given implementation. It must have the following behavior:

- Accept a path to a JSON file as a positional argument, e.g., my_dingus /path/to/test_case.json
- Exit code 1 if there is an error that is not related to validation (e.g., file not found)
- If the validation passes, exit code 0 and print a JSON object to stdout with the following keys:
  - `validity`: "valid"
  - `message` (optional): a string describing the result of the validation
- If the validation fails, exit code 0 and print a JSON object to stdout with the following keys:
  - `validity`: "invalid"
  - `message` (optional): a string describing the reason for the failure
