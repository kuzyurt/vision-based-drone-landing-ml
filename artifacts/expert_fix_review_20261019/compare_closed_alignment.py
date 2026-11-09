from pathlib import Path
import argparse,json,math
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')
def stats(ep):
    assert(ep/'preview_result.json').exists();rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];chosen=[];resets=[]
    for r in rows:
        d=r['output'].get('learner_diagnostics')or{};o=r['observation'];p=o['px4']
        if(d.get('expert_marker_localizer')or{}).get('destructive_metric_reset'):resets.append(r['task_time_s'])
        if(d.get('expert_intent')or{}).get('phase')=='target_align'and o['gimbal_rad'][1]>math.radians(60)and p.get('armed')and not p.get('landed'):chosen.append(r)
    angles=np.unwrap([r['observation']['gimbal_rad'][0]+math.pi/2-r['observation']['px4']['attitude_ned_rad'][2]for r in chosen]);times=np.array([r['task_time_s']for r in chosen]);steps=np.diff(times);consecutive=(steps>0)&(steps<.081)
    rates=np.abs(np.diff(angles)[consecutive])/steps[consecutive]*180/math.pi
    near=[r for r in chosen if(r['output']['learner_diagnostics'].get('estimated_clearance_m')or 99)<1]
    return dict(last_task_s=rows[-1]['task_time_s'],near_nadir_align_rows=len(chosen),world_camera_pan_variation_deg=float(np.sum(abs(np.diff(angles)[consecutive]))*180/math.pi),pan_rate_deg_s_p95=float(np.percentile(rates,95))if len(rates)else None,
        visibility_hold_rows=sum(bool(r['output']['learner_diagnostics'].get('nearfield_descent_paused'))for r in chosen),camera_sync_hold_rows=sum(bool(r['output']['learner_diagnostics'].get('camera_sync_descent_hold'))for r in chosen),
        near_deck_align_rows=len(near),destructive_metric_reset_task_s=resets),chosen
def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);a=p.parse_args();out=ROOT/'expert_fix_review_20261019'/a.revision;report={}
    for case,old in [('E01','expert_visible_native_v18'),('E03','expert_visible_native_v16')]:
        if not(out/case/'preview_result.json').exists():continue
        new,chosen=stats(out/case);oldstat,_=stats(ROOT/old);report[case]=dict(old=oldstat,new=new,interpretation='matched scenario; native closed-loop trajectories differ; development demonstration, not broad reliability')
        sheet=Image.new('RGB',(1280,4*390),(12,18,25));picks=[chosen[int(f*(len(chosen)-1))]for f in np.linspace(0,1,8)]
        with h5py.File(out/case/'observations.h5','r')as h:
            for i,r in enumerate(picks):
                x=i%2*640;y=i//2*390;sheet.paste(Image.fromarray(np.asarray(h['rgb'][r['frame_index']])),(x,y));d=r['output']['learner_diagnostics']
                ImageDraw.Draw(sheet).text((x+4,y+362),f"actual {r['task_time_s']:.2f}s {d.get('control_phase')} sync {d.get('camera_sync_error_deg')}deg",fill='white')
        sheet.save(out/(case+'_alignment_sequence.jpg'),quality=94)
    dest=out/'alignment_comparison_v2.json';assert not dest.exists();dest.write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
