# Rebuilding the corrected assembly

Run `python tools/build_all.py` from smartdrone2. It uses the Python bundled with the installed FreeCAD 1.1, reads the original document, creates the inventory, exports transformed meshes, and rebuilds the viewer and MuJoCo XML. Set FREECAD_PYTHON if FreeCAD is installed elsewhere. The source is never recomputed or saved.

Run `python -m sim.server`; the inspection viewer is available at http://127.0.0.1:8793/inspection/. Its packed geometry is stored in 8 MiB binary chunks, avoiding one oversized generated JavaScript file.

The viewer validates every resting mesh against source bounds, then checks simultaneous camera and propeller motion against independent rotation formulas. `python tests/verify_mjcf.py` checks the full-resolution native inspection model after a complete CAD rebuild; `python tests/verify_flight.py` checks the bundled flight model.

Camera limits follow the owner's specification: continuous xaxis pan and yaxis tilt from −61° to +140°. To apply edited limits to the inspection XML, download the JSON and run `python tools/make_mjcf.py --limits path/to/joint_limits.json`. Regenerate the flight scene afterwards with `tools/make_flight_scene.py`. The four propeller hinges remain unlimited.

`models/drone.xml` is an inspection model with a fixed drone base and visual meshes without collisions. Its inertias come from the component mass ledger. `models/flight.xml` adds a free aircraft, gravity, collision proxies, propulsion, PX4 control and articulated onboard camera. Read [flight_model.md](flight_model.md) for sources, physical assumptions, launch instructions and the measurements still required for real-flight calibration.

The retired conversion/GUI-bridge scripts and saved backup documents were archived outside this project during cleanup. The active pipeline uses `tools/build_corrected.py` and never recomputes or saves the source assembly in `cad/`.
