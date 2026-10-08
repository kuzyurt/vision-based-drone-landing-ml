# Run the flight lab

The supported launch configuration is Windows, Python 3.12, desktop OpenGL, and WSL2 Ubuntu 22.04. PX4 runs in WSL; MuJoCo and the local web server run in Windows. Linux/macOS launch has not been implemented or tested.

## One-time PX4 setup

Install WSL2 Ubuntu 22.04 using Microsoft's instructions. In that distribution, change into this checkout's WSL path (for example `/mnt/d/projects/smartdrone2`) and run:

```bash
bash tools/setup_px4.sh --install-deps
```

This obtains official PX4 v1.16.0 at commit `6ea3539157ca358c70a515878b77077af7d4611d`, installs the vendor's Ubuntu build dependencies, applies the documented battery-message correction, and builds SITL. Source and firmware live in `~/.cache/smartdrone2/`. The installer may request your Ubuntu sudo password. This downloads/builds firmware, not the Gazebo simulator. If dependencies are already installed, omit `--install-deps`.

## Windows launch

From the checkout in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[build,test]"
python -m sim.server
```

Open <http://127.0.0.1:8793/>. Wait for PX4 ready, then press Take off. Reset scene restarts the simulated aircraft and PX4 estimator together; the selected wind preset/seed are retained and their sequence restarts. The inspection viewer is served at `/inspection/` by the same process.

The default distribution name is `Ubuntu-22.04`; set `PX4_WSL_DISTRO` if yours has a different name. Repository paths are resolved at launch and are not tied to the original author's drive. Ports are TCP4560 (HIL simulator), UDP14541 (Offboard/telemetry) and localhost HTTP8793. One flight-lab instance at a time owns those simulator ports.

The committed flight meshes and metadata let you run without FreeCAD. Full CAD re-export requires FreeCAD 1.1 and the optional build dependencies; see [rebuild.md](rebuild.md). `build/` contains disposable model caches, generated parameters and logs. Close with Ctrl+C in the server terminal; it stops only the PX4 process recorded and verified by this project.

## Checks

```powershell
python tests/check_environment.py
python tests/verify_flight.py
python tests/check_live.py
python tests/check_upgrade_live.py
```

The live check needs the server running and takes control of the simulated aircraft. It ends landed/disarmed. Reports are saved in `build/`; no hardware connection is used.
