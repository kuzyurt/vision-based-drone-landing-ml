"""Rebuild from the source using FreeCAD Python, without a GUI bridge."""
import os
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
(ROOT/'build').mkdir(exist_ok=True)
(ROOT/'models/metadata').mkdir(parents=True,exist_ok=True)
fc = os.environ.get('FREECAD_PYTHON', str(Path(os.environ['LOCALAPPDATA'])/'Programs/FreeCAD 1.1/bin/python.exe'))
if not Path(fc).is_file():
    raise SystemExit('Set FREECAD_PYTHON to the Python executable bundled with FreeCAD.')
subprocess.run([fc, '-u', str(ROOT/'tools/build_corrected.py'), '--export'], cwd=ROOT, check=True)
subprocess.run([fc,'-u',str(ROOT/'tools/cad_mass_properties.py')],cwd=ROOT,check=True)
for script in ('materials.py', 'make_viewer.py', 'build_mass_model.py', 'make_mjcf.py', 'build_flight_meshes.py', 'build_aerodynamics.py', 'make_flight_scene.py'):
    subprocess.run([sys.executable, str(ROOT/'tools'/script)], cwd=ROOT, check=True)
