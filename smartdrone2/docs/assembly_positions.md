# Original assembly position and joint inventory

Source: `drone+camera+other-things.FCStd`. SHA256: `ec033c1fe230e5b7499c5350c3b8b6143f8a4317d1df383274c7a4acb0af10c0`.

The saved scene is Z-up. The main-drone group has translation (-19.5, 100, 115) mm and roll +90 degrees. Every nested LinkGroup transform and every linked-group instance must be applied. Source objects reused by links are rendered once per visible assembly path.

Hierarchy: drone -> fixed camera mount -> xaxis pan -> yaxis tilt + rigid black cover. The mounting plate Body002 and Compound001 mount are fixed. Only CombinedShell and Shell003/Body004 articulate.

| Body / joint | Parent | Pivot XYZ (mm) | Axis XYZ | Motion |
|---|---|---|---|---|
| base_link | world | 0.000000, 0.000000, 0.000000 | fixed | rigid |
| camera_mount | base_link | 0.000000, 0.000000, 0.000000 | fixed | rigid |
| cam_x_pan | camera_mount | -19.598976, 100.084488, 70.500000 | [0, 0, 1] | xaxis: left / right (pan) |
| cam_y_tilt | cam_x_pan | -11.994240, 70.000000, 0.000000 | [0, 1, 0] | yaxis: up / down (tilt) |
| prop_1 | base_link | 157.500000, -77.000000, 173.500000 | [0, 0, 1] | 10x4.5R-front-right |
| prop_2 | base_link | 157.500000, 276.500000, 173.500000 | [0, 0, 1] | 10x4.5R-front-left |
| prop_3 | base_link | -196.000000, 276.500000, 173.500000 | [0, 0, 1] | 10x4.5R-back-left |
| prop_4 | base_link | -196.000000, -77.000000, 173.500000 | [0, 0, 1] | 10x4.5R-back-right |

Camera pivots use the centres of the circular marker edges, rather than body-placement origins or shell bounding boxes. Propeller pivots use concentric hub circles, rather than blade bounding boxes.

Pan rotates continuously through 360 degrees. The user-specified tilt range is -61 to +140 degrees; zero preserves the saved assembly pose.

All positions and angles are listed in [positions.csv](positions.csv); the full hierarchy, quaternions and bounds are in ../models/metadata/position_inventory.json.

Imported open camera surfaces can have enormous analytic BRep bounding boxes. The inventory uses tessellated bounds, which correspond to the visible surface. Wire-only PCB artwork is recorded but does not produce a triangle mesh.

313 visible leaf instances; 307 contain triangles.

Four source motor instances overlap exactly; the viewer and MJCF render each once (303 meshes). The inspection MJCF has a fixed base with mass-ledger inertials. `models/flight.xml` supplies the free aircraft, flight scene, physical motor/gimbal actuators and onboard camera. See [mass and flight model evidence](flight_model.md).
