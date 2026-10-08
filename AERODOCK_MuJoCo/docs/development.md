# Commands and development

## Python control

```python
from boat_sim import BoatSim

boat = BoatSim()
boat.new_world("island", seed=42, path_seed=43)
boat.run_for(10)
boat.manual_control()
boat.set_motor_power(port=30, starboard=45)
print(boat.get_speed())
```

Mechanism commands: `open_lid()`, `close_lid()`, `raise_platform()`, `lower_platform()`.
Propulsion commands: `start_motor()`, `stop_motor()`, `emergency_stop()` and `set_motor_power(port, starboard)`.
Navigation commands: `new_world()`, `new_path()`, `follow_path()` and `manual_control()`.
Advance simulation time with `step()` or `run_for(seconds)`; the server advances it automatically.

HTTP commands use `POST /api/command/{name}` with a JSON argument object. State is available at `GET /api/status` and `/api/world`; camera images at `/frame/forward.jpg` and `/frame/dock.jpg`. The running server's `/docs` lists the full API.

## Files

| Location | Contents |
|---|---|
| `cad/` | Native FreeCAD document and standalone macro |
| `models/`, `assets/` | MJCF, complete part manifest, meshes and textures |
| `usv/`, `web/` | Physics, drainage, navigation, scenery, server and browser controls |
| `config.json` | Water, propulsion and rendering settings |
| `examples/worlds/` | Five seeded world/route examples |
| `tools/` | CAD export, textures, media, telemetry, benchmarks and packaging |
| `tests/`, `reports/` | Verification scripts and saved results |
| `docs/` | Media, technical notes and texture provenance |

## Rebuild and check

```powershell
python -m tests.verify_simulation
python -m tests.verify_cameras
python -m tools.package_delivery
```

Optional test tooling is listed in `requirements-dev.txt`. Rebuild the CAD/MJCF with `python -m tools.export_freecad` from a FreeCAD-enabled Python environment.

The documentation stills use Blender 4.5+ with Cycles. Install Blender and put `blender` on PATH, or set `BLENDER_EXE` to its executable:

```powershell
$env:BLENDER_EXE = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
python -m tools.generate_media --stills
```

The renderer imports every CAD mesh in its simulation pose. It adds studio lighting and material finishes without changing the simulation. Exterior textures use physical coordinates rather than stretched UVs; interior materials have no texture maps. The cutaway hides the hull, deck, covers, hull trim and both service hatch frames/seals only for the image.

Regenerate the simulated animations with `python -m tools.generate_media --island` or `--dock`. Running without a flag rebuilds all four media files.
