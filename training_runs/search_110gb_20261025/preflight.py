"""Read-only dependency/plan checks; optional model and renderer contract probes."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
from common import (HERE, REPO, LOCAL, config, make_plan, sha, source_receipt,
                    summary_counts, verify_sources, configure_simulation_imports)


def check(physics=False, neural=False, backend=False):
    if os.name!='nt':raise RuntimeError('This prepared collector uses the audited Windows PX4 backend')
    for name in ('numpy','PIL','torch','torchvision','mujoco','pymavlink','scipy','psutil','cv2'):
        if importlib.util.find_spec(name) is None:raise RuntimeError('Missing dependency: '+name)
    if shutil.which('node') is None:raise RuntimeError('Node.js not found')
    sources=source_receipt();verify_sources(sources)
    runtime=json.loads((REPO/'benchmark/environments/runtime.json').read_text())
    for name,expected in runtime['px4_hashes'].items():
        if sha(REPO/'tidewater-game/app/public/landing/wasm'/name)!=expected:raise ValueError('PX4 differs from current benchmark')
    plan=make_plan()
    from landing_training import paths
    from benchmark.runner import make_scenario
    for e in plan:make_scenario(e).validate()
    if len({e['scenario']['world_seed'] for e in plan})!=len(plan):raise ValueError('Repeated world')
    c=config()
    if not c['dataset_budget_bytes']+10000000000<=c['total_budget_bytes']:
        raise ValueError('No room for models/overhead')
    raw_bound=6000*(640*360*3+32768+2048)
    if raw_bound>c['database_limit_bytes'] or c['database_limit_bytes']+100000000>c['episode_reservation_bytes']:
        raise ValueError('Episode reservation is insufficient for worst-case RGB/labels')
    result=dict(status='preflight_passed',**summary_counts(plan),source_hashes=len(sources),
        collection_started=False,model_probe=False,renderer_probe=False)
    if neural:
        import torch
        from model import load_backbone, SearchHead, encode_maps, targets, loss
        torch.set_num_threads(1);torch.manual_seed(c['seed'])
        base=load_backbone('cpu');head=SearchHead()
        fine,context=encode_maps(base,torch.zeros(1,3,360,640,dtype=torch.uint8))
        target={k:v[None] for k,v in targets([]).items()}
        value,_=loss(head(fine,context),target)
        if not torch.isfinite(value):raise ValueError('Nonfinite empty-view loss')
        value.backward()
        if any(p.grad is not None for p in base.parameters()):raise ValueError('Base is not frozen')
        result.update(model_probe=True,feature_shapes=[list(fine.shape),list(context.shape)],loss=float(value.detach()))
    if physics:
        configure_simulation_imports()
        import mujoco
        from landing_training import environment,rendering
        from windows_renderer import OnboardRenderer
        from target_learning.scenes import annotation_groups
        from target_learning.label_renderer import install,identify_water
        from landing_training.privileged_teacher import VisibleBoatOracle
        from storage import pack_rgb,unpack_rgb
        install(rendering)
        class Renderer(OnboardRenderer):
            def append_water(self,scene):
                super().append_water(scene);identify_water(scene,self.env)
        model=mujoco.MjModel.from_binary_path(str(REPO/runtime['scene']))
        environment.compile_scene=lambda *a,**kw:model
        env=environment.Environment(make_scenario(plan[0]))
        renderer=Renderer(env)
        try:
            rgb=renderer.onboard_image()
            renderer.onboard.enable_segmentation_rendering()
            try:seg=renderer.onboard.render().copy()
            finally:renderer.onboard.disable_segmentation_rendering()
            views=VisibleBoatOracle(env,annotation_groups(model)).observe(seg)
            codec,blob=pack_rgb(rgb)
            if unpack_rgb(codec,blob).tobytes()!=rgb.tobytes():raise ValueError('Renderer roundtrip failed')
            result.update(renderer_probe=True,rgb_bytes=len(blob),visible_instances=len(views),physics_steps=0)
        finally:renderer.close()
    if backend:
        import tempfile
        from simulation import run_episode
        with tempfile.TemporaryDirectory(prefix='search110_disarmed_probe_') as directory:
            result['backend_probe']=run_episode(dict(entry=plan[0],output=str(Path(directory)/'probe'),
                slot=0,source_fingerprint='validation_only',disarmed_backend_probe=True))
    print(json.dumps(result,indent=2),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',action='store_true');p.add_argument('--renderer',action='store_true')
    p.add_argument('--backend',action='store_true',help='Disarmed four-second PX4/physics validation, no task/data')
    args=p.parse_args();check(physics=args.renderer,neural=args.model,backend=args.backend)
