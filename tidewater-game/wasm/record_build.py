"""Record pinned source, compiler and shipped artifact hashes after a build."""
from pathlib import Path
import hashlib,json,subprocess,sys
cache=Path(sys.argv[1]);root=Path(__file__).resolve().parent;out=root.parent/'app/public/landing/wasm'
revision=lambda path:subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
px4=revision(cache/'px4-wasm-source');sdk=revision(cache/'emsdk')
if px4!='6ea3539157ca358c70a515878b77077af7d4611d' or sdk!='62a853cd3b3134398ce85cde8bb5cbb2ef0194cb':raise RuntimeError('Source pin changed')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'px4_revision':px4,'emsdk_revision':sdk,'emscripten_version':'4.0.10','mujoco_version':'3.14.0','source_hashes':{p.name:sha(p) for p in sorted(root.iterdir()) if p.suffix in ('.cpp','.hpp','.py','.sh','.txt')},'artifacts':{name:{'sha256':sha(out/name),'bytes':(out/name).stat().st_size} for name in ('px4.mjs','px4.wasm')}}
(out/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
