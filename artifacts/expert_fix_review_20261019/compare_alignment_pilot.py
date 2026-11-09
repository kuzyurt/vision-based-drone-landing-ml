from pathlib import Path
import json,math
import h5py,numpy as np
from PIL import Image,ImageDraw
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z');OUT=ROOT/'expert_fix_review_20261019/v26b'
def stats(ep,case):
    assert(ep/'preview_result.json').exists();rows=[json.loads(l)for l in(ep/'steps.jsonl').open()];selected=[];holds=0
    for r in rows:
        d=r['output'].get('learner_diagnostics')or{};o=r['observation'];p=o['px4']
        if (d.get('expert_intent')or{}).get('phase')=='target_align'and o['gimbal_rad'][1]>math.radians(60)and p.get('armed')and not p.get('landed'):
            selected.append(r);holds+=int(bool(d.get('nearfield_descent_paused')))
    angles=np.unwrap([r['observation']['gimbal_rad'][0]+math.pi/2-r['observation']['px4']['attitude_ned_rad'][2]for r in selected]);time=np.array([r['task_time_s']for r in selected]);dt=np.diff(time)
    rates=np.abs(np.diff(angles))/np.maximum(dt,1e-8)*180/math.pi
    lateral=[r['output']['learner_diagnostics']['estimated_lateral_error_m']for r in selected if r['output']['learner_diagnostics'].get('estimated_lateral_error_m')is not None]
    result=dict(selected_rows=len(selected),world_camera_pan_total_variation_deg=float(np.sum(np.abs(np.diff(angles)))*180/math.pi),pan_rate_deg_s_p95=float(np.percentile(rates,95)),estimated_lateral_error_m_p95=float(np.percentile(lateral,95))if lateral else None,visibility_hold_rows=holds,last_task_s=rows[-1]['task_time_s'])
    if case.startswith('new'):
        sheet=Image.new('RGB',(1280,1170));picks=[selected[int(f*(len(selected)-1))]for f in [0,.2,.4,.6,.8,1]]
        with h5py.File(ep/'observations.h5','r')as h:
            for i,r in enumerate(picks):
                x=i%2*640;y=i//2*390;sheet.paste(Image.fromarray(np.asarray(h['rgb'][r['frame_index']])),(x,y));d=r['output']['learner_diagnostics'];ImageDraw.Draw(sheet).text((x+5,y+362),f"actual {r['task_time_s']:.2f}s {d.get('control_phase')} pan={r['observation']['gimbal_rad'][0]*180/math.pi:.1f} deg",fill='white')
        sheet.save(OUT/(case+'_alignment_rgb.jpg'),quality=94)
    return result
reports={}
for case,old in [('E01','expert_visible_native_v18'),('E05','expert_visible_native_v15_recovery')]:
    reports[case]={'new':stats(OUT/case,'new_'+case)}
    if case=='E01':reports[case]['old']=stats(ROOT/old,'old_'+case)
out=OUT/'alignment_comparison.json';assert not out.exists();out.write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2))
