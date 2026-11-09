from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parent
def main():
    case=ROOT/'search_v42/pilots/learner_struggle';rows=[json.loads(x)for x in(case/'steps.jsonl').open()]
    for i in [0,50,100,200,300,500,700,900,len(rows)-1]:
        r=rows[i];d=r['output'].get('learner_diagnostics')or{};dg=d.get('dagger')or{};e=dg.get('trigger_evidence')or{};print(json.dumps(dict(frame=i,task_s=r.get('task_time_s'),phase=d.get('control_phase'),own_z=r['observation']['px4']['position_enu_m'][2],learner_fit=d.get('marker_center_px'),learner_metric=d.get('metric_confirmed'),learner_acceptance=d.get('metric_acceptance'),teacher_confirmed=e.get('target_confirmed'),teacher_pose_valid=e.get('pad_pose_valid'),teacher_shadow=d.get('expert_shadow_intent'),wrong_selected=dg.get('wrong_candidate_selected_by_learner'),struggle=dg.get('struggle_evidence')),separators=(',',':')))
    print('LIVE',subprocess.check_output(['ps','-u','hxhshsh7gyg','-o','pid,ppid,etimes,args'],text=True)[-18000:])
if __name__=='__main__':main()
