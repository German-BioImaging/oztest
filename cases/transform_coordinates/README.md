# Coordinate transformation test cases

These test cases are intended to test the numerical accuracy of coordinate transformation implementations.
They do NOT test implementations' capability to transform images on the basis of those coordinate transformations.

## Test case layout

Each test case is an OME-Zarr hierarchy with a Scene in the root node.
This Scene contains a graph of coordinate systems joined by coordinate transformations.

At the root of each OME-Zarr hierarchy is a `conformance.toml` file, which lays out:

```toml
description = "The first case of my comprehensive and totally correct test suite."

# result should be within 0.000_001 of expected value
absolute_tolerance = 1e-06

# result should be within 0.1% of expected value
relative_tolerance = 0.001

[source]
name = "inputSystem"  # name of the input coordinate system
coordinates = [
  [ -1, -1, -1 ],  # first 3D input coordinate
  [ 0, 0, 0 ],  # second 3D input coordinate
]

[target]
name = "outputSystem"  # name of the output coordinate system
coordinates = [
  [ 18, 57, 16 ],  # first 3D expected output coordinate
  [ 20, 60, 120 ],  # second 3D expected output coordinate
]
```

Users of the conformance tests should

1. open the OME-Zarr hierarchy
2. parse the Scene
3. construct the coordinate system graph
4. find a path through the graph from the input to the output coordinate system
5. apply the resulting coordinate transform sequence to the input coordinates
6. check that the resulting coordinates equal the given output coordinates, to within the given tolerances

raising an error if any of these steps are not possible.

## Dingus signature

Implementors may use the `oztest` tool in combination with their own dingus CLI to manage running the tests.

The call to the dingus, including any prefix arguments, should be added to the end of an invocation of `oztest transform-coordinates`.
`oztest` will then supply 4 additional positional arguments.

```sh
#!/bin/sh
oztest transform_coordinates -- myDingus -somearg --another=arg something somethingelse
```

The last 4 positional arguments of the dingus MUST be:

- `PATH`: a path to an OME-Zarr hierarchy on the file system
- `INPUT`: the name of the input coordinate system
- `OUTPUT`: the name of the output coordinate system
- `COORDINATES`: a JSON-serialised array of D-length arrays of numbers, where D is the dimensionality of a single coordinate

For the example above, the dingus would see invocations like

```sh
myDingus -somearg --another=arg something somethingelse '/path/to/testcase.ome.zarr' 'inputSystem' 'outputSystem' '[[-1,-1,-1],[0,0,0]]'
```

The dingus MUST then

1. open the OME-Zarr hierarchy at `PATH` and parse the Scene from the attributes
2. calculate a transformation from the coordinate system with name specified by `SOURCE` to the coordinate system with name specified by `TARGET` (this may require inverting one or more transforms)
3. apply this transformation to the `COORDINATES` array
4. print to STDOUT a JSON-serialised [Response](#object-response) object
5. exit with status code 0

If any of the above steps are not supported by the implementation, the dingus MUST exit with a status code other than 0.
In this case, it MAY print to STDOUT a JSON-serialised [Error](#object-response) object.

For the example above, a passing test would exit with status code 0 after printing

```json
{"coordinates":[[18,57,16],[20,60,120]]}
```

### Object: Response

| field | necessity | type | description |
| ----- | --------- | ---- | ----------- |
| coordinates | MUST | array of array of number | The resulting coordinates from transforming the input. |
| message | MAY | string | Free-text details. |

### Object: Error

| field | necessity | type | description |
| ----- | --------- | ---- | ----------- |
| message | MAY | string | Free-text description of error. |
