from pathlib import Path
import json
import generate_context_v8 as g
root=Path(__file__).resolve().parent
job=dict(name='training_000',role='training',seed=990000,map='island',frames=32,
    directory=str(root/'context_smoke_v8b'),model_sha256=g.old.sha(root/'hard_scene_probe_v3/hard_scene.mjb'))
if __name__=='__main__':
    report=g.generate(job)
    import h5py
    with h5py.File(report['path'],'r')as h:
        examples=[dict(frame=i,instances=[p for p in json.loads(v)['instances']if p['annotation_instance']in ['target','decoy_blank_clone']])for i,v in enumerate(h['labels'])]
    g.old.save(root/'context_smoke_v8b_report.json',dict(report=report,examples=examples))
    print(json.dumps(dict(report=report,examples=examples)),flush=True)

