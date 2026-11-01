# Coordinate transformation test cases

These test cases are intended to test the numerical accuracy of coordinate transformation implementations.
They do NOT test implementations' capability to transform images on the basis of those coordinate transformations.

## Test case layout

Each test case is an OME-Zarr hierarchy with a Scene in the root node.
This Scene contains a graph of coordinate systems joined by coordinate transformations.

At the root of each OME-Zarr hierarchy is an `oztest.json` file, which lays out:

```jsonc
{
    "description": "The first case of my comprehensive and totally correct test suite.",
    "transform_coordinates": {
        "tolerance": {  // optional, defaults as shown
            "relative": 0.00001,  // optional, default as shown
            "absolute": 0.00000001  // optional, default as shown
        },
        "source": {
            // input coordinate system name
            "name": "mySourceCoordinateSystem",
            "coordinates": [
                // first input coordinate
                [-1, -1, -1],
                // second input coordinate
                [0, 0, 0]
            ]
        },
        "target": {
            // output coordinate system name
            "name": "myTargetCoordinateSystem",
            "coordinates": [
                // expected result of transforming first input coordinate
                [ 18, 57, 16 ],
                // expected result of transforming second input coordinate
                [ 20, 60, 120 ]
            ]
        }
    }
}
```

Users of the conformance tests should

1. open the OME-Zarr hierarchy
2. parse the Scene
3. construct the coordinate system graph
4. find a path through the graph from the input to the output coordinate system
5. apply the resulting coordinate transform sequence to the input coordinates
6. check that the resulting coordinates are close to the given output coordinates, using the `numpy.allclose` algorithm
    `|a - b| <= (absolute + relative * |b|)`

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

For the example above, a passing test would exit with status code 0 after printing

```json
{"coordinates":[[18,57,16],[20,60,120]]}
```

### Object: Response

| field | necessity | type | description |
| ----- | --------- | ---- | ----------- |
| coordinates | MUST | array of array of number | The resulting coordinates from transforming the input. |
| message | MAY | string | Free-text details. |
| xfail | MAY | boolean, default `false` | Whether the dingus expected to fail this test. |
