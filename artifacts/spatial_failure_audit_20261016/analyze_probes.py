"""Assess recorded image localization and registration; do not train on these images."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import collections,hashlib,importlib.util,json,math,sys
from pathlib import Path
import h5py,numpy as np,torch
from PIL import Image,ImageDraw,ImageFont

BASE=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml')
OLD=BASE/'landing_training/outputs/domain_training_20261016T134939Z'
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE));sys.path.insert(0,str(OLD))
import landing_training
landing_training.__path__.append(str(OLD/'candidate_bundle/code/landing_training'))
from landing_training import paths
from landing_training.radio_robust_20261015.model import RadioRobustPoseModel


def summarize(values):
    a=np.asarray(values,dtype=float)
    return dict(n=len(a),median=float(np.median(a)),p90=float(np.percentile(a,90)),rms=float(np.sqrt(np.mean(a*a)))) if len(a) else None


def main():
    torch.set_num_threads(1)
    if not (OUT/'probe_result.json').exists():raise RuntimeError('Wait for both bounded probes to finish')
    saved=torch.load(OLD/'candidate_bundle/pose.pt',map_location='cuda',weights_only=False)
    model=RadioRobustPoseModel().cuda();model.load_state_dict(saved['model']);model.eval()
    p=OLD/'candidate_bundle_v3/code/landing_training/radio_robust_20261015/acquisition.py'
    spec=importlib.util.spec_from_file_location('audited_existing_acquisition',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    heads={}
    for name in ['v3','v4']:
        head=module.AcquisitionHead().cuda();head.load_state_dict(torch.load(OLD/f'candidate_bundle_{name}/acquisition.pt',map_location='cuda',weights_only=False)['model']);head.eval();heads[name]=head
    results=[];panels=[]
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',16)
    for directory in sorted(OUT.glob('probe_*/')):
        rows=[json.loads(x) for x in (directory/'steps.jsonl').read_text().splitlines()]
        rows=[r for r in rows if not r.get('terminal',False)]
        visible=[r for r in rows if r['privileged']['pad_visible']]
        active=[r for r in visible if r['output']['learner_diagnostics']['raw_model_visibility_probability']>=.8]
        metrics={}
        for label,selected in [('pad_visible',visible),('pad_visible_and_confident',active)]:
            errors=[np.linalg.norm(np.array(r['output']['learner_diagnostics']['learned_center_px'])-r['privileged']['pad_keypoints_px'][0]) for r in selected]
            metrics[label]=summarize(errors)
        sampled=[r for r in visible if r['frame_index']%4==0]
        comparison={}
        with h5py.File(directory/'observations.h5','r') as f,torch.inference_mode():
            values={name:[] for name in heads};baseline=[]
            for start in range(0,len(sampled),16):
                batch=sampled[start:start+16]
                images=np.stack([f['rgb'][r['frame_index']] for r in batch])
                tensor=torch.from_numpy(images).permute(0,3,1,2)[:,None].cuda()
                features=model.backbone.encode_images(tensor)
                targets=np.array([r['privileged']['pad_keypoints_px'][0] for r in batch])
                baseline.extend(np.linalg.norm(np.array([r['output']['learner_diagnostics']['learned_center_px'] for r in batch])-targets,axis=1).tolist())
                for name,head in heads.items():
                    predictions=head(features)[:,0].cpu().numpy();pixels=(predictions[:,1:]+1)*[320,180]
                    values[name].extend(np.linalg.norm(pixels-targets,axis=1).tolist())
            comparison['baseline_same_frames']=summarize(baseline)
            for name,errors in values.items():comparison[name]=summarize(errors)
            selected=[]
            for wanted in [19.,22.]:
                candidates=[r for r in active if abs(r['task_time_s']-wanted)<2.]
                if not candidates:candidates=active or visible
                row=min(candidates,key=lambda r:abs(r['task_time_s']-wanted))
                selected.append(row)
            for row in selected:
                rgb=f['rgb'][row['frame_index']];image=Image.new('RGB',(680,455),'#111b29');image.paste(Image.fromarray(rgb),(20,56));draw=ImageDraw.Draw(image)
                diag=row['output']['learner_diagnostics'];truth=row['privileged']['pad_keypoints_px'][0];pred=diag['learned_center_px']
                for point,color in [(truth,'#36ff9b'),(pred,'#ffcf55')]:
                    x,y=point[0]+20,point[1]+56
                    draw.ellipse((x-9,y-9,x+9,y+9),outline=color,width=3);draw.line((x-14,y,x+14,y),fill=color,width=2);draw.line((x,y-14,x,y+14),fill=color,width=2)
                draw.text((15,8),f"{directory.name.replace('probe_test_','')} | t={row['task_time_s']:.1f}s",font=font,fill='white')
                draw.text((15,31),f"Model score {diag['raw_model_visibility_probability']:.3f} | error {np.linalg.norm(np.array(pred)-truth):.1f}px",font=font,fill='white')
                draw.text((15,421),'Green: true pad | yellow: neural prediction',font=font,fill='#cddbea');panels.append(image)
        result=dict(name=directory.name,frames=len(rows),visible_frames=len(visible),metrics=metrics,existing_head_comparison=comparison,
            registration_rejections=dict(collections.Counter(r['output']['learner_diagnostics']['registration_debug'].get('registration_rejection','not_attempted') for r in rows)),
            rgb_source_sha256=hashlib.sha256((directory/'steps.jsonl').read_bytes()).hexdigest())
        results.append(result);print(json.dumps(result),flush=True)
    canvas=Image.new('RGB',(1360,910),'#111b29')
    for i,panel in enumerate(panels):canvas.paste(panel,((i%2)*680,(i//2)*455))
    canvas.save(OUT/'actual_rgb_localization_errors.jpg',quality=94)
    result=dict(cases=results,new_training=False,evaluation_only=True,
        comparison_caveat='Existing v3/v4 image heads evaluated offline on sampled baseline RGB. Pixel error alone does not establish closed-loop landing success.',
        overlays='Exact recorded RGB with diagnostic truth/prediction annotations. Truth is not fed to policy.')
    (OUT/'probe_analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
