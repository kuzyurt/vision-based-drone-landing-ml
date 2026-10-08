"""Build a portable archive and verify every MJCF asset is in it."""
import hashlib
from datetime import date
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT.parent/'AERODOCK_MuJoCo_COMPLETE.zip'

if __name__=='__main__':
    files=[]
    manifest=json.loads((ROOT/'models/manifest.json').read_text())
    cad=json.loads((ROOT/'reports/cad_validation.json').read_text())
    simulation=json.loads((ROOT/'reports/simulation_validation.json').read_text())
    part_count=manifest['exported_part_count']
    keep={'.py','.json','.xml','.md','.txt','.bat','.FCStd','.html','.css','.js','.png','.jpg','.csv','.gif'}
    for p in ROOT.rglob('*'):
        if not p.is_file() or '__pycache__' in p.parts or '.venv' in p.parts or p.name in ('delivery_checksums.json','scenery_previous_state.json','_organize.py'): continue
        if 'previews' in p.parts:continue
        if '_debug' in p.stem or p.stem in ('procedural_island_raw','procedural_mesh_smallwater'):continue
        if p.suffix in keep or p.name=='.gitignore' or (p.suffix=='.obj' and 'assets' in p.parts): files.append(p)
    report={'date':date.today().isoformat(),'archive':ARCHIVE.name,'part_count':part_count,
            'cad_checks':cad['checks'],'simulation_checks':simulation['checks'],'files':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (ROOT/'reports/delivery_checksums.json').write_text(json.dumps(report,indent=2))
    files.append(ROOT/'reports/delivery_checksums.json')
    with zipfile.ZipFile(ARCHIVE,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for p in files: archive.write(p,'AERODOCK_MuJoCo/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        names=set(archive.namelist())
        root=ET.fromstring(archive.read('AERODOCK_MuJoCo/models/boat.xml'))
        for asset in root.findall('./asset/mesh'):
            assert 'AERODOCK_MuJoCo/assets/meshes/'+asset.attrib['file'] in names
        for asset in root.findall('./asset/texture'):
            if 'file' in asset.attrib: assert 'AERODOCK_MuJoCo/assets/textures/'+asset.attrib['file'] in names
        manifest=json.loads(archive.read('AERODOCK_MuJoCo/models/manifest.json'))
        assert manifest['cad_part_count']==manifest['exported_part_count']==len(manifest['parts'])==part_count
        print('Archive verified: %d files, %d parts, %.2f MB'%(len(names),part_count,ARCHIVE.stat().st_size/1e6))
