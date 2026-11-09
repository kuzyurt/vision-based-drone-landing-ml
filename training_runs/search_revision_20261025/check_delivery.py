"""Check every proposed fresh world at the planned airborne pose, without flight."""
import math
import tempfile
from pathlib import Path
import numpy as np
from common import REPO, HERE, make_plan, configure_simulation_imports, write_json


def main():
    configure_simulation_imports()
    import mujoco
    from landing_training import environment, rendering
    from landing_training.privileged_teacher import VisibleBoatOracle
    from benchmark.runner import make_scenario
    from mission_setup import VerticalLaunchEnvironment
    from review_helpers import place_distractors
    from windows_renderer import OnboardRenderer
    from target_learning.label_renderer import install, identify_water
    from delivery import visibility_probe
    install(rendering)
    class Renderer(OnboardRenderer):
        def append_water(self,scene):
            super().append_water(scene);identify_water(scene,self.env)
    reports=[]
    with tempfile.TemporaryDirectory(prefix='revision_delivery_') as tmp:
        VerticalLaunchEnvironment.audit_directory=Path(tmp)
        for entry in make_plan():
            model=mujoco.MjModel.from_binary_path(str(REPO/'artifacts/city80_decoys_20261023/scene.mjb'))
            environment.compile_scene=lambda *a,**kw:model
            env=VerticalLaunchEnvironment(make_scenario(entry))
            groups=place_distractors(env,Path(tmp))
            for index,name in enumerate(sorted(k for k in groups if k!='target')):
                yaw=entry['decoy_yaws'][index];mid=int(model.body_mocapid[model.body(name).id])
                env.data.mocap_quat[mid]=[math.cos(yaw/2),0,0,math.sin(yaw/2)]
                retain=entry['false_boat_unsimilar'] if 'unsimilar' in name else entry['false_boat_similar']
                if retain==0:
                    gids=groups.pop(name);model.geom_group[gids]=5
                    model.geom_contype[gids]=0;model.geom_conaffinity[gids]=0
            q=env.drone.free_qadr
            env.data.qpos[q:q+2]=env.task_start_xy
            mujoco.mj_forward(model,env.data)
            env.data.qpos[q+2]+=entry['scenario']['height']-env.vertical_clearance
            mujoco.mj_forward(model,env.data)
            renderer=Renderer(env)
            try: report=visibility_probe(env,renderer,VisibleBoatOracle(env,groups))
            finally:renderer.close()
            report.update(id=entry['id'],pass_check=report['detectable_headings']>=2)
            reports.append(report);print(report,flush=True)
    write_json(HERE/'delivery_checks.json',dict(status='passed' if all(r['pass_check'] for r in reports) else 'failed',episodes=reports,flight=False))
    if not all(r['pass_check'] for r in reports):raise RuntimeError('Proposed worlds need redesign')


if __name__=='__main__':main()
