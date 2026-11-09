"""Complete the established cache schema, using the actual recorded teacher data."""
import json
from pathlib import Path
import h5py,numpy as np

def complete(root,file_hash,save):
    manifest=root/'features/manifest.json';data=json.loads(manifest.read_text())
    backup=root/'features/manifest.before_compatibility.json'
    if not backup.exists():save(backup,data)
    for e in data['entries']:
        cache=Path(e['cache'])
        assert cache.resolve().is_relative_to((root/'features').resolve())
        with h5py.File(cache,'a') as dst:
            if 'actions' not in dst or 'valid' not in dst:
                with h5py.File(e['source_path']) as raw:
                    rows=[json.loads(x) for x in raw['steps']]
                if 'actions' not in dst:
                    dst.create_dataset('actions',data=np.array([r['output'].get('expert_bounded_action',r['output']['executed_action']) for r in rows],dtype='f4'))
                if 'valid' not in dst:
                    dst.create_dataset('valid',data=np.array([not r.get('terminal',False) and r['output'].get('action_supervision_valid',True) for r in rows],dtype='f4'))
                dst.attrs['action_cache_note']='Actual recorded teacher actions retained for schema compatibility; this experiment trains pose heads, not action imitation'
        e['cache_sha256']=file_hash(cache)
    save(manifest,data)
