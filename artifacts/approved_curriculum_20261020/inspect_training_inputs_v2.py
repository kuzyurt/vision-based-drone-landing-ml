from pathlib import Path
import json,h5py
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[3] if False else Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training')
m=json.loads((BASE/'datasets/expert/manifest.json').read_text())
e=next(e for e in m['episodes']if e['role']=='training')
with h5py.File(BASE/'datasets/expert'/e['path'],'r')as h:
    indices=[0,min(300,len(h['steps'])-1),min(700,len(h['steps'])-1)]
    print(json.dumps(dict(entry=e,attrs={k:str(v)for k,v in h.attrs.items()},datasets={k:list(h[k].shape)for k in h},samples=[json.loads(h['steps'][i])for i in indices]),indent=2))
for p in [ROOT.parent/'train_design_and_marker_v12.py',ROOT.parent/'train_perception_v24.py',ROOT.parent/'collection_pipeline',ROOT.parent/'perception_training_v24']:
    print('EXISTS',str(p),p.exists())
print('ROOTFILEMATCHES',[p.name for p in ROOT.parent.glob('*train*v1*.py')])
