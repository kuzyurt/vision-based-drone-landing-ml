"""Closed-only audit/export with explicit ownership; never data admission."""
from pathlib import Path
import argparse,json,os,select,subprocess,sys
ROOT=Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/target_discrimination_20261018T175843Z')

def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--cases',nargs='+',required=True);a=p.parse_args();out=ROOT/'expert_fix_review_20261019'/a.revision
    dest=out/'packaging_v2_state.json';assert not dest.exists()
    def save(**v):
        temp=dest.with_suffix('.tmp');temp.write_text(json.dumps(dict(pid=os.getpid(),training_eligible=False,**v),indent=2));temp.replace(dest)
    try:
        pid=json.loads((out/'launch.json').read_text())['pid'];save(status='waiting_for_closed_recordings',coordinator=pid)
        try:fd=os.pidfd_open(pid)
        except ProcessLookupError:fd=None
        if fd is not None:
            try:ready=select.select([fd],[],[],7200)[0];assert ready,'bounded coordinator wait expired'
            finally:os.close(fd)
        state=json.loads((out/'state.json').read_text());assert state['status']=='completed',state
        deliveries=[]
        for case in a.cases:
            with(out/(case+'_audit_v2.log')).open('x')as log:
                subprocess.run([sys.executable,str(ROOT/'audit_replacement_review_v2.py'),'--revision',a.revision,'--case',case],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            audit=json.loads((out/(case+'_audit.json')).read_text())
            assert not audit['command_history_mismatches']and not audit['unsupported_descent']and not audit['metric_wrong'],'invalid teacher commands, history or wrong-object metric'
            assert audit['exact_valid_rgb_joins']==audit['valid_images'],'valid actual RGB must join exact capture annotation'
            assert audit['outcome']in ['landed','home_landed']
            rows=[json.loads(l)for l in(out/case/'steps.jsonl').open()]
            # Primary whole flight only when every task action is teacher/fault.
            # Mixed cases export explicit expert segments, never relabel learner.
            blocks=audit['owner_blocks'];mixed=any(b['owner']=='policy'for b in blocks)
            jobs=[]
            if not mixed:
                jobs.append(('full',None,None))
                if case!='E12':jobs.append(('alignment_1x',max(0.,rows[-1]['task_time_s']-28.),rows[-1]['task_time_s']))
            else:
                for i,b in enumerate(blocks):
                    if b['owner']in ['expert','expert_prefix']and b['end_task_s']-b['start_task_s']>=2:jobs.append(('expert_segment_'+str(i),b['start_task_s'],b['end_task_s']))
            if audit['actual_fault_rows']:
                first=rows[audit['actual_fault_rows'][0]]['task_time_s'];jobs.append(('fault_recovery_1x',max(0.,first-2),first+26))
            for suffix,start,end in jobs:
                name='expert_fix_review_20261019/'+a.revision+'/'+case+'_corrected_'+suffix
                args=[sys.executable,str(ROOT/'export_replacement_preview.py'),'--episode','expert_fix_review_20261019/'+a.revision+'/'+case,'--name',name,'--max-seconds','30']
                if start is not None:args+=['--start-task',str(start),'--end-task',str(end)]
                with(out/(case+'_'+suffix+'_package.log')).open('x')as log:subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
                receipt=json.loads((ROOT/(name+'_video_receipt.json')).read_text());deliveries.append(receipt)
            save(status='packaging_closed_actual_cameras',latest_case=case,deliveries=deliveries)
        save(status='completed_needs_visual_review',deliveries=deliveries)
    except BaseException as error:save(status='failed',error=repr(error));raise
if __name__=='__main__':main()
