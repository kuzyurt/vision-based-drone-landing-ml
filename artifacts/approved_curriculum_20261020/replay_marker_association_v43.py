"""Read-only SAME-INPUT teacher replay; no physical prediction or training."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
from pathlib import Path
import hashlib,json,sys,time
import h5py,numpy as np,torch
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'search_v42/sources'))
from target_learning.expert_adapter_v42 import IdentityExpert
def main():
    torch.set_num_threads(1);case=ROOT/'search_v42/pilots/learner_struggle';out=ROOT/'search_v42/association_diagnosis';out.mkdir(exist_ok=False);rows=[json.loads(x)for x in(case/'steps.jsonl').open()];binding=json.loads((ROOT/'search_v42/candidate_binding.json').read_text());actor=IdentityExpert(ROOT.parents[1]/'landing_hardening_20261018T011610Z/candidate_r15',binding['checkpoint'],review_only=True,package_name='same_input_association_diagnosis');results=[];start=time.monotonic();sustained=None;first=None
    with h5py.File(case/'observations.h5','r')as h:
        for r in rows:
            if r.get('terminal'):break
            i=r['frame_index'];o=r['observation'];ld=r['output'].get('learner_diagnostics')or{};rgb=np.asarray(h['rgb'][i]);action,ed=actor.act(rgb,o);evidence=dict(frame=i,task_s=r.get('task_time_s'),teacher_confirmed=bool(ed.get('expert_observable_target_confirmed')),teacher_pixel=ed.get('marker_center_px'),learner_pixel=ld.get('marker_center_px'),teacher_metric=bool(ed.get('metric_valid')and ed.get('metric_confirmed')),learner_metric=bool(ld.get('metric_valid')and ld.get('metric_confirmed')),teacher_acceptance=ed.get('metric_acceptance'),learner_acceptance=ld.get('metric_acceptance'),teacher_rms=ed.get('marker_fit_rms_px'),learner_rms=ld.get('marker_fit_rms_px'),teacher_clearance=ed.get('estimated_clearance_m'),learner_clearance=ld.get('estimated_clearance_m'),learner_action=r['output']['executed_action'],own_vertical_speed=o['px4']['velocity_enu_m_s'][2])
            a=evidence['teacher_pixel'];b=evidence['learner_pixel'];different=False
            if a is not None and b is not None:
                evidence['pixel_separation']=float(np.linalg.norm(np.asarray(a)-np.asarray(b)));evidence['conservative_disagreement_threshold_px']=max(32.,6.*(float(evidence['teacher_rms']or 0)+float(evidence['learner_rms']or 0)))
                different=bool(evidence['teacher_confirmed']and evidence['teacher_metric']and evidence['learner_metric']and ed.get('metric_acceptance')=='tracked'and ld.get('metric_acceptance')=='tracked'and evidence['pixel_separation']>evidence['conservative_disagreement_threshold_px'])
            motion=np.linalg.norm(np.asarray(evidence['learner_action'])[:2])>.3 or(evidence['own_vertical_speed']<-.15 and evidence['learner_action'][2]>.02)
            sustained=(float(r['task_time_s'])if sustained is None else sustained)if different and motion else None;evidence['association_disagrees']=different;evidence['observed_actual_motion']=bool(motion);evidence['sustained_disagreement_s']=0. if sustained is None else float(r['task_time_s'])-sustained
            if i%25==0 or different:results.append(evidence)
            if evidence['sustained_disagreement_s']>=3:
                first=evidence;break # Stop at first changed decision; never predict its physical outcome.
    report=dict(status='closed_same_input_diagnosis',frames_replayed=i+1,first_three_second_current_fit_disagreement=first,rows=results,wall_s=time.monotonic()-start,teacher_source_sha256=hashlib.sha256(Path(sys.modules[IdentityExpert.__module__].__file__).read_bytes()).hexdigest(),recognizer_sha256=binding['recognizer_sha256'],failed_raw_used_for_training=False,physical_counterfactual_claimed=False,truth_actor_input=False);(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='rows'}),flush=True)
if __name__=='__main__':main()
