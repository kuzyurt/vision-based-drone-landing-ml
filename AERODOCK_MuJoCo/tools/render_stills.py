"""Ray-traced documentation stills from the complete, posed MuJoCo CAD assembly.

Requires Blender 4.5+ (BLENDER_EXE, PATH, or the local portable renderer cache).
Intermediate scene data lives in a temporary directory, never in the delivery.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import numpy as np
from PIL import Image
from boat_sim import BoatSim, ROOT, quaternion
from usv.rendering import cutaway_geom_ids


def render_stills():
    executable = os.environ.get('BLENDER_EXE') or shutil.which('blender')
    if not executable:
        cache = Path(os.environ.get('LOCALAPPDATA', '')) / 'aerodock-render'
        candidates = sorted(cache.glob('blender-*/blender-local.exe'), reverse=True)
        candidates += sorted(cache.glob('blender-*/blender.exe'), reverse=True)
        executable = candidates[0] if candidates else None
    if not executable:
        raise RuntimeError('Install Blender 4.5+ and set BLENDER_EXE to its executable.')
    sim = BoatSim({'wave_height': 0})
    sim.data.qpos[:3] = 0
    sim.data.qpos[3:7] = quaternion(0, 0, 0)
    sim.refresh_transforms()
    hidden = cutaway_geom_ids(sim)
    arrays, records = {}, []
    for part in sim.manifest['parts']:
        for mesh in part['meshes']:
            gid = sim.model.geom(mesh['name']).id
            mid = int(sim.model.geom_dataid[gid])
            va, vn = int(sim.model.mesh_vertadr[mid]), int(sim.model.mesh_vertnum[mid])
            fa, fn = int(sim.model.mesh_faceadr[mid]), int(sim.model.mesh_facenum[mid])
            key = str(len(records))
            # Compiled vertices include MuJoCo's mesh recentering; apply the
            # corresponding geom transform, rather than guessing CAD offsets.
            arrays['v'+key] = sim.model.mesh_vert[va:va+vn] @ sim.data.geom_xmat[gid].reshape(3,3).T + sim.data.geom_xpos[gid]
            arrays['f'+key] = sim.model.mesh_face[fa:fa+fn].copy()
            records.append({'key': key, 'name': mesh['name'], 'part': part['name'],
                            'color': part['metadata']['color'], 'material': part['material'],
                            'textured': bool(mesh['texture']), 'hidden': gid in hidden,
                            'helper': part['group'] >= 4})
    with tempfile.TemporaryDirectory(prefix='aerodock-studio-') as temporary:
        folder = Path(temporary)
        np.savez(folder/'geometry.npz', **arrays)
        (folder/'scene.json').write_text(json.dumps(records))
        subprocess.run([str(executable), '--background', '--factory-startup', '--python-exit-code', '1', '--python',
                        str(ROOT/'tools/blender_studio.py'), '--', str(folder), str(ROOT/'docs/media')], check=True)
    with Image.open(ROOT/'docs/media/boat_exterior.png') as rendered:
        resolution = list(rendered.size)
    return {'resolution': resolution, 'cad_parts': len(sim.manifest['parts']),
            'cad_meshes': len(records), 'renderer': 'Blender Cycles',
            'materials': 'painted composite, satin metal, rubber, brass and optical glass; metric procedural exterior textures',
            'cutaway_hides': sorted({r['part'] for r in records if r['hidden']})}
