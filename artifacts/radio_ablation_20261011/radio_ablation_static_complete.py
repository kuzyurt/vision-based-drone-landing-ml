"""Review-only full radio disconnection with unchanged v5 policy/supervisor."""
import os,json,copy,collections
from pathlib import Path
os.environ.update(MUJOCO_GL='egl',LANDING_REUSE_APPROVED_RUNTIME='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
import torch,numpy as np
from landing_training.config import Scenario
from landing_training.marker_bundle import load_bundle,read_bundle
from landing_training.gate import file_hash
from landing_training import run_episode as episode
from landing_training.recording import numeric_observation

ROOT=Path('landing_training/outputs/radio_ablation_static_complete_20261011')
BUNDLE=Path('landing_training/outputs/marker_iteration_20261010T233621Z/policy_bundle_v5/policy.json')

class DisconnectedBeacon:
    def __init__(self,seed):pass
    def sample(self,env,px4):
        return dict(sequence=0,age_s=10.,valid=False,dock_ready=False,relative_heading_m=[0.,0.,0.],velocity_heading_m_s=[0.,0.,0.],source='SX1262_inputs_removed')

def main():
    torch.set_num_threads(1);ROOT.mkdir(exist_ok=False);read_bundle(BUNDLE)
    scenarios=[Scenario(name='radio_removed_static_complete',distance=3.,height=3.,boat_speed=0.,duration=45.)]

    plan=dict(policy_bundle_sha256=file_hash(BUNDLE),policy_unchanged=True,supervisor_unchanged=True,radio_removed_before_observation=True,cases=[s.__dict__ for s in scenarios],qualification='Original MuJoCo environment. No radio position, velocity or dock-ready input. Original expert warm-up/takeoff only, then frozen hybrid commands.')
    (ROOT/'plan.json').write_text(json.dumps(plan,indent=2));episode.Beacon=DisconnectedBeacon;results=[]
    for index,s in enumerate(scenarios):
        policy=load_bundle(BUNDLE,'cuda');policy.reset()
        class AuditedPolicy:
            metadata=policy.metadata
            def act(self,rgb,obs):
                b=obs['beacon'];assert not b['valid'] and not b['dock_ready']
                assert b['relative_heading_m']==b['velocity_heading_m_s']==[0.,0.,0.]
                numeric=numeric_observation({'observation':obs});assert np.array_equal(numeric[11:17],np.zeros(6))
                return policy.act(rgb,obs)
        directory=ROOT/s.name
        summary=episode.run_episode(s,directory,role='review',video=False,instance=255+index,controller=AuditedPolicy(),record_images=True)
        rows=[json.loads(x) for x in (directory/'steps.jsonl').read_text().splitlines()]
        actions=[r for r in rows if not r.get('terminal')]
        assert all(not r['observation']['beacon']['valid'] and not r['observation']['beacon']['dock_ready'] for r in rows)
        result=dict(name=s.name,outcome=summary['outcome'],records=summary['records'],radio_inputs_zero_every_frame=True,
                    learned_visibility_mean=float(np.mean([r['output']['learner_diagnostics']['raw_model_visibility_probability'] for r in actions])),
                    metric_valid_frames=sum(r['output']['learner_diagnostics']['metric_valid'] for r in actions),
                    phases=dict(collections.Counter(r['output']['learner_diagnostics']['control_phase'] for r in actions)),
                    interventions=dict(collections.Counter(r['output']['intervention'] for r in actions)),events=summary['events'])
        results.append(result);read_bundle(BUNDLE)
        (ROOT/'report.json').write_text(json.dumps(dict(status='running' if len(results)<len(scenarios) else 'completed',policy_bundle_sha256=file_hash(BUNDLE),results=results),indent=2))
        print('RADIO_ABLATION_RESULT',json.dumps(result),flush=True)

if __name__=='__main__':main()
