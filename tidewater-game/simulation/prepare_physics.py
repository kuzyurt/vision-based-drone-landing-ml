"""Prepare an invariant-checked, collision-only Linux model from the original CAD."""
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
import server

def prepare():
    source = server.compile_scene(.001)
    root = ET.parse(server.REPO/'landing_training/build/combined_1000us.xml').getroot()
    for parent in root.iter():
        for geom in list(parent.findall('geom')):
            name = geom.get('name', '')
            gid = mujoco.mj_name2id(source, mujoco.mjtObj.mjOBJ_GEOM, name)
            if gid >= 0 and name != 'water_surface' and not name.startswith('shore_contact_') and source.geom_contype[gid] == 0 and source.geom_conaffinity[gid] == 0:
                parent.remove(geom)
            else:
                geom.attrib.pop('material', None)
    used = {g.get('mesh') for g in root.iter('geom') if g.get('mesh')}
    asset = root.find('asset')
    for item in list(asset):
        if item.tag in ('texture', 'material') or (item.tag == 'mesh' and item.get('name') not in used):
            asset.remove(item)
    xml = server.RUNTIME/'physics-base-windows.xml'
    ET.ElementTree(root).write(xml, encoding='unicode')
    model = mujoco.MjModel.from_xml_path(str(xml))
    for key in ('body_mass', 'body_inertia', 'body_ipos', 'body_iquat', 'jnt_axis'):
        if not np.array_equal(getattr(source, key), getattr(model, key)):
            raise RuntimeError(f'Preparation changed original {key}')
    mujoco.mj_saveModel(model, str(server.RUNTIME/'physics-base.mjb'))
    (server.RUNTIME/'visual-layout.json').write_text(json.dumps(server.visual_layout_from(source)))
    for item in root.iter():
        file = item.get('file')
        if file and len(file) > 2 and file[1] == ':':
            item.set('file', '/mnt/'+file[0].lower()+'/'+file[3:].replace('\\', '/'))
    ET.ElementTree(root).write(server.RUNTIME/'physics-base-linux.xml', encoding='unicode')
    print(f'Prepared original physics: {model.ngeom} geoms, {model.nmesh} collision meshes', flush=True)

if __name__ == '__main__':
    prepare()
