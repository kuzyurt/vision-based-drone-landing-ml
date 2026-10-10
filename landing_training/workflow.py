"""Resumable reviewed expert collection, pilot checks, training and evaluation."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import shutil
import sys
import threading
import time
import uuid

from . import cloud_collection as cloud
from .cloud_collection import CloudCollection,StageFailed
from .collection_session import atomic_json,tree_bytes
from .collect import planned_scenarios,approved_bundle
from .gate import file_hash,source_fingerprint,compatible_runtime_fingerprints
from .status import snapshot,stage_times,display
from .progress import atomic_text

ROOT=Path(__file__).resolve().parent


class DatasetAuditFailed(StageFailed):
    def __init__(self,stage,detail):
        super().__init__(stage,2)
        self.args=('Dataset audit rejected recordings: '+detail,)


def verify_runtime_resume(state,runtime,manifest_path):
    accepted=compatible_runtime_fingerprints(runtime)
    if state.get('review_authorization',{}).get('runtime_sha256') not in accepted:
        raise ValueError('Source changed since this pipeline began; unchanged approved runtime proof is required to resume')
    manifest_path=Path(manifest_path)
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        for entry in manifest['episodes']:
            artifact=(manifest_path.parent/entry['path']).resolve()
            if not artifact.is_relative_to(manifest_path.parent.resolve()):raise ValueError('Dataset path escapes its directory')
            summary=json.loads(artifact.parent.joinpath('summary.json').read_text())
            if summary.get('runtime_source_sha256') not in accepted:
                raise ValueError('Recorded episode runtime changed: '+entry['name'])


def storage_reserve(plan,minimum_gb):
    feature_bytes=sum((math.ceil(item['scenario']['duration']*25)+1)*7108
                      for item in plan['episodes'] if item['role']!='test')
    # Evaluation stores JSONL only and stops flight logging after PX4 startup.
    # Small bootstrap ULogs remain covered by the logs/checkpoint allowance.
    # 16 KiB/decision, 4 GB logs/checkpoints, plus 15% feature-file overhead.
    evaluation_count=252
    evaluation_bytes=evaluation_count*(180*25+1)*16384+4*10**9
    return minimum_gb+math.ceil((feature_bytes*1.15+evaluation_bytes)/10**9)


def completion(manifest_path,entries):
    path=Path(manifest_path)
    if not path.exists():return False
    manifest=json.loads(path.read_text());expected={e['scenario']['name'] for e in entries}
    actual=[e['name'] for e in manifest['episodes']]
    if len(actual)!=len(set(actual)):raise ValueError('Duplicate indexed episode')
    if set(actual)-expected:raise ValueError('Dataset contains episodes outside this stage plan')
    return set(actual)==expected


def pilot_policy_check(report):
    if report.get('status')!='completed':raise ValueError('Policy pilot did not finish')
    outcomes=report['outcomes'];success=outcomes.get('landed',0)
    unsafe=outcomes.get('water_strike',0)+outcomes.get('collision_failure',0)
    return {'passed':success>0 and unsafe==0,'landed':success,'unsafe':unsafe,
            'criterion':'At least one landing and zero unsafe pilot outcomes are required to continue the epoch budget. '
                        'This is a minimum learning check, not qualification of landing reliability.'}


class Pipeline(CloudCollection):
    def __init__(self,args):
        self.guard=threading.RLock();self.heartbeat_stop=threading.Event();self.heartbeat=None
        self.state_path=Path(args.state).resolve();self.state_path.parent.mkdir(parents=True,exist_ok=True)
        old=json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.configuration={key:str(Path(getattr(args,key)).resolve()) if key in ('output','checkpoints') else getattr(args,key)
                            for key in ('output','checkpoints','epochs','pilot_epochs','patience','workers','evaluation_workers','reader_workers','min_free_gb','max_dataset_gb','device')}
        if old and old['configuration']!=self.configuration:raise ValueError('Pipeline settings changed: select a new --state file/output or restore previous settings')
        self.state=old or {'schema':'aerodock.landing.pipeline.v1','configuration':self.configuration,'milestones':{},'stages':[]}
        self.interrupted=[stage for stage in self.state['stages'] if stage['status'] in ('running','recovery_pending')]
        for stage in self.interrupted:
            stage['elapsed_seconds']=max(stage.get('elapsed_seconds',0.),stage.get('observed_elapsed_seconds',0.))
            stage['status']='recovery_pending'
        self.prior_seconds=self.state.get('elapsed_total_seconds',0.)
        super().__init__(args)
        self.stages=self.state['stages'];self.checkpoints=Path(args.checkpoints).resolve();self.manifest=self.dataset/'manifest.json'
        def filesystem(path):
            while not path.exists():path=path.parent
            return path.stat().st_dev
        if len({filesystem(p) for p in (self.dataset,self.checkpoints,self.folder,self.state_path.parent)})!=1:
            raise ValueError('Dataset, checkpoints and reports must share the guarded filesystem')
        self.progress_failure=None
        self.state['planned_episodes']=len(planned_scenarios()['episodes'])
        self.state['latest_launch']=str(self.folder);self.state['configuration']=self.configuration
        (ROOT/'outputs/latest_pipeline_launch.txt').write_text(str(self.folder)+'\n')

    def save(self):
        with self.guard:
            super().save()
            launch=json.loads((self.folder/'launch_status.json').read_text())
            self.state.update(status=self.status,active_stage=self.stage,exit_code=self.code,stop_reason=self.reason,
                              elapsed_total_seconds=self.prior_seconds+time.monotonic()-self.started,
                              updated_utc=datetime.now(timezone.utc).isoformat(),stages=self.stages,
                              latest_launch=str(self.folder),dataset_directory=str(self.dataset),
                              dataset_GB=launch['dataset_GB'],episodes_total=launch['episodes_total'])
            if self.manifest.exists():
                indexed=json.loads(self.manifest.read_text())['episodes']
                self.state.update(episodes_total=len(indexed),dataset_GB=tree_bytes(self.dataset)/10**9,
                                  dataset_splits=dict(Counter(e['role'] for e in indexed)))
            self.state['checkpoint_and_cache_GB']=tree_bytes(self.checkpoints)/10**9
            self.state['disk_free_GB']=shutil.disk_usage(self.folder).free/10**9
            self.state['elapsed_total_hours']=self.state['elapsed_total_seconds']/3600
            self.state['stage_seconds'],self.state['timing']=stage_times(self.state)
            for stage in self.stages:
                if stage.get('status')=='running' and stage.get('started_utc'):
                    stage['observed_elapsed_seconds']=max(0.,
                        (datetime.now(timezone.utc)-datetime.fromisoformat(stage['started_utc'])).total_seconds())
            current=snapshot(self.state)
            self.state['progress']=current['progress']
            atomic_json(self.state_path,self.state);atomic_json(self.folder/'pipeline_report.json',self.state)
            atomic_text(self.folder/'summary.txt',display(current)+'\n')

    def pulse(self):
        while not self.heartbeat_stop.wait(30):
            try:self.save()
            except Exception as exc:
                self.progress_failure=exc
                self.reason='Pipeline progress write failed: '+str(exc)
                if self.child and self.child.poll() is None:self.child.terminate()
                return

    def run(self):
        self.heartbeat=threading.Thread(target=self.pulse,daemon=True);self.heartbeat.start()
        try:return super().run()
        finally:
            self.heartbeat_stop.set();self.heartbeat.join(timeout=5);self.save()

    def run_stage(self,*args,**kwargs):
        if self.progress_failure:raise RuntimeError('Progress monitoring failed') from self.progress_failure
        result=super().run_stage(*args,**kwargs)
        if self.progress_failure:raise RuntimeError('Progress monitoring failed') from self.progress_failure
        return result

    def milestone(self,name,value):
        self.state['milestones'][name]=value;self.save()

    def resolve_review(self):
        try:bundle=approved_bundle(self.args.review)
        except PermissionError as exc:
            if self.args.review!='auto':raise
            if getattr(self.args,'no_review_export',False):
                self.status='user_review_required';self.stage='awaiting_user_review';self.code=2
                self.reason='Automatic review-video export was disabled. '+str(exc)
                return None
            runtime=source_fingerprint(runtime_only=True)
            bundle=ROOT/'outputs'/('pipeline_review_'+runtime[:16])
            (self.folder/'current_review').symlink_to(bundle.resolve(),target_is_directory=True)
            self.run_stage('qualification',[sys.executable,'-u','-m','landing_training.qualify'])
            self.run_stage('review_export',[sys.executable,'-u','-m','landing_training.review','--output',str(bundle),'--workers','4'])
            manifest=json.loads((bundle/'manifest.json').read_text())
            if not manifest['qualification_passed']:raise StageFailed('review_qualification',1)
            self.state['review_bundle']=str(bundle);self.status='user_review_required';self.stage='awaiting_user_review';self.code=2
            self.reason='Verify all ten current videos, recorded data and qualification before approving this review.'
            self.emit('Review page: '+str(bundle/'index.html')+'\n');return None
        self.state['review_bundle']=str(bundle)
        alias=self.folder/'current_review'
        if not alias.exists():alias.symlink_to(Path(bundle).resolve(),target_is_directory=True)
        return bundle

    def collect_to(self,bundle,entries,reserve,label):
        current=json.loads(self.manifest.read_text())['episodes'] if self.manifest.exists() else []
        names={item['name'] for item in current};expected={item['scenario']['name'] for item in entries}
        # Later-stage episodes on resume are allowed; every indexed name must
        # still belong to the complete, frozen plan verified by the final audit.
        missing=expected-names
        if not missing:return
        report_dir=self.folder/'results';report_dir.mkdir(exist_ok=True)
        self.run_stage(label,[sys.executable,'-u','-m','landing_training.collect','--review',bundle,
             '--output',str(self.dataset),'--max-episodes',str(len(missing)),
             '--workers',str(self.args.workers),'--instance-base','20','--gl','egl','--require-gpu',
             '--min-free-gb',str(reserve),'--max-dataset-gb',str(self.args.max_dataset_gb),
             '--quarantine-partial','--report-dir',str(report_dir)])
        report=json.loads((report_dir/'latest.json').read_text())
        self.milestone(label,{'report':str(report_dir/'latest.json'),'status':report['status'],
                             'episodes':report['episodes_total'],'dataset_GB':report['dataset_GB']})
        indexed={e['name'] for e in json.loads(self.manifest.read_text())['episodes']}
        if report['status']!='completed' or not expected.issubset(indexed):
            self.status='stopped';self.code=3;self.reason='Collection incomplete: '+str(report.get('stop_reason'));return False
        return True

    def audit(self,pilot=False):
        from .outcome_retries import RETRY_LIMIT
        output=self.folder/('pilot_audit.json' if pilot else 'dataset_audit.json')
        label='pilot_audit' if pilot else 'dataset_audit'
        self.milestone(label,{'report':str(output),'passed':False})
        command=[sys.executable,'-u','-m','landing_training.dataset_audit','--manifest',str(self.manifest),'--output',str(output),'--allow-retried-aborts']
        if pilot:command.append('--pilot')
        for round_number in range(RETRY_LIMIT+1):
            failure=None
            try:self.run_stage(label,command)
            except StageFailed as exc:
                if exc.code!=2 or not output.is_file():raise
                failure=exc
            report=json.loads(output.read_text())
            self.milestone(label,{'report':str(output),'passed':report['passed'],
                                  'warnings':report.get('quality_warnings',[])})
            if report['passed']:
                for warning in report.get('quality_warnings',[]):self.emit('DATA QUALITY NOTE: '+warning+'\n')
                return report
            candidates=report.get('retry_candidates',[])
            critical=report.get('error') or report.get('missing_episodes') or report.get('unsafe_expert_flights')
            if critical or not candidates or round_number==RETRY_LIMIT:
                detail=report.get('error') or json.dumps({key:report.get(key) for key in
                    ('missing_episodes','unsafe_expert_flights','nominal_expert_failures','nominal_landing_rates')})
                self.emit('Audit cannot continue: '+detail+'\n')
                raise DatasetAuditFailed(label,detail) from failure
            if (self.checkpoints/'latest.pt').exists():raise ValueError('Cannot replace dataset episodes after training has started')
            reserve=storage_reserve(planned_scenarios(),self.args.min_free_gb)
            retry_label='pilot_retry_collection' if pilot else 'dataset_retry_collection'
            self.emit(f'Retrying {len(candidates)} nominal non-landings; successful episodes stay untouched.\n')
            results=self.folder/'results';results.mkdir(exist_ok=True)
            self.run_stage(retry_label,[sys.executable,'-u','-m','landing_training.collect',
                '--review',self.state['review_bundle'],'--output',str(self.dataset),
                '--max-episodes',str(len(candidates)),'--workers',str(min(self.args.workers,len(candidates))),
                '--instance-base','20','--gl','egl','--require-gpu','--quarantine-partial',
                '--min-free-gb',str(reserve),'--max-dataset-gb',str(self.args.max_dataset_gb),
                '--report-dir',str(results),'--retry-names',*candidates])
            retry_report=json.loads((results/'latest.json').read_text())
            if retry_report['status']!='completed':
                raise RuntimeError('Retry collection stopped: '+str(retry_report.get('stop_reason')))

    def train_to(self,bundle,epochs,label):
        latest=self.checkpoints/'latest.pt'
        if latest.exists():
            import torch
            checkpoint=torch.load(latest,map_location='cpu',weights_only=False)
            if checkpoint['dataset_sha256']!=file_hash(self.manifest):raise ValueError('Training checkpoint belongs to a different dataset')
            if checkpoint['review_manifest_sha256']!=file_hash(Path(bundle)/'manifest.json'):raise ValueError('Training checkpoint belongs to a different review')
            if not (self.checkpoints/'best.pt').exists():raise ValueError('Incomplete checkpoint set: best.pt is missing')
            if checkpoint['epoch']>=epochs or (self.args.patience and checkpoint['bad_epochs']>=self.args.patience):return
        command=[sys.executable,'-u','-m','landing_training.train','--review',bundle,'--manifest',str(self.manifest),
                 '--output',str(self.checkpoints),'--epochs',str(epochs),'--device',self.args.device,
                 '--loader-workers',str(self.args.reader_workers),'--cpu-threads','4','--patience',str(self.args.patience)]
        if latest.exists():command.append('--resume')
        self.run_stage(label,command)
        self.milestone(label,{'result':str(self.checkpoints/'training_result.json')})

    def evaluation(self,bundle,label,split,count,stratified=False):
        # Retries retain their traces. Recheck actual free space on each attempt.
        needed=count*(180*25+1)*16384+self.args.min_free_gb*10**9
        if shutil.disk_usage(self.dataset).free<needed:raise OSError('Insufficient free space for evaluation and shutdown reserve')
        checkpoint=self.checkpoints/'best.pt';digest=file_hash(checkpoint)
        old=self.state['milestones'].get(label)
        if old and old.get('checkpoint_sha256')==digest:
            report_path=Path(old['report'])
            if report_path.exists():
                report=json.loads(report_path.read_text())
                if report['status']=='completed' and report['dataset_sha256']==file_hash(self.manifest):return report
        output=self.folder/(label+'_'+uuid.uuid4().hex[:8])
        command=[sys.executable,'-u','-m','landing_training.evaluate','--manifest',str(self.manifest),'--review',bundle,
                 '--checkpoint',str(checkpoint),'--split',split,'--max-episodes',str(count),'--output',str(output),
                 '--device',self.args.device,'--cpu-threads','1','--workers',str(self.args.evaluation_workers)]
        if stratified:command.append('--stratified')
        self.run_stage(label,command);report=json.loads((output/'report.json').read_text())
        self.milestone(label,{'checkpoint_sha256':digest,'report':str(output/'report.json')})
        return report

    def recover_interrupted(self):
        """Finish an owned child job before quarantining any of its recordings."""
        import psutil,signal
        from .px4 import stop_owned_native_runtime
        for stage in self.interrupted:
            pid=stage.get('child_pid');created=stage.get('child_create_time');command=stage.get('command')
            if pid is None or created is None or command is None:
                raise RuntimeError('Interrupted stage has no ownership journal; stop its old job before using a fresh state')
            self.emit('Recovering interrupted stage: '+stage['name']+'\n')
            try:
                process=psutil.Process(pid)
                if process.create_time()!=created or os.getpgid(pid)!=pid:
                    raise RuntimeError('Interrupted child PID ownership changed; refusing to stop another process')
                if process.status()!=psutil.STATUS_ZOMBIE and process.cmdline()!=command:
                    raise RuntimeError('Interrupted child command changed; refusing to stop another process')
                process.terminate()
                deadline=time.monotonic()+45
                while process.is_running() and process.status()!=psutil.STATUS_ZOMBIE and time.monotonic()<deadline:
                    time.sleep(.1)
                if process.is_running() and process.status()!=psutil.STATUS_ZOMBIE:
                    os.killpg(pid,signal.SIGKILL);deadline=time.monotonic()+5
                    while process.is_running() and process.status()!=psutil.STATUS_ZOMBIE and time.monotonic()<deadline:time.sleep(.1)
                    if process.is_running() and process.status()!=psutil.STATUS_ZOMBIE:raise RuntimeError('Interrupted child did not stop')
            except (psutil.NoSuchProcess,ProcessLookupError):pass
            scopes=[self.dataset]
            if '--output' in command:
                output=Path(command[command.index('--output')+1]).resolve()
                if not output.is_relative_to(ROOT) and not output.is_relative_to(self.dataset):
                    raise RuntimeError('Interrupted output escaped the owned workflow scope')
                scopes.append(output)
            for scope in set(scopes):
                if scope.is_dir():
                    for journal in scope.rglob('owned_process.json'):stop_owned_native_runtime(journal.parent)
            recovered=datetime.now(timezone.utc)
            # An abrupt stop has no known finish time: don't count offline hours.
            stage['elapsed_seconds']=max(stage.get('elapsed_seconds',0.),stage.get('observed_elapsed_seconds',0.))
            stage['timing_note']='Last observed running time; unreported work before interruption may be missing.'
            stage.update(status='interrupted_recovered',recovered_utc=recovered.isoformat())
            self.save()

    def execute(self):
        self.recover_interrupted()
        if getattr(self.args,'reuse_approved_runtime',False):
            os.environ['LANDING_REUSE_APPROVED_RUNTIME']='1'
        self.run_stage('gpu_probe',[sys.executable,'-u','-c',
            'import torch; from landing_training.collection_benchmark import renderer_info; '
            'info=renderer_info(); print(info,flush=True); '
            'assert not info["software_rendering"], "NVIDIA EGL required"; '
            'assert torch.cuda.is_available(), "CUDA PyTorch required"'])
        bundle=self.resolve_review()
        if bundle is None:return
        source=source_fingerprint()
        previous_source=self.state.get('source_sha256',source)
        runtime=source_fingerprint(runtime_only=True)
        if previous_source!=source:
            if not getattr(self.args,'reuse_approved_runtime',False):
                raise ValueError('Source changed since this pipeline began; unchanged approved runtime proof is required to resume')
            verify_runtime_resume(self.state,runtime,self.manifest)
            previous_runtime=self.state.get('review_authorization',{}).get('runtime_sha256')
            correction=previous_runtime!=runtime
            reason=('Exact short-rock-tile renderer crash correction; previously successful scenery unchanged.'
                    if correction else 'Explicitly reuse approved, unchanged simulation runtime and plan after orchestration changes.')
            self.state.setdefault('source_migrations',[]).append({
                'previous_source_sha256':previous_source,'current_source_sha256':source,
                'previous_runtime_sha256':previous_runtime,
                'runtime_sha256':runtime,'updated_utc':datetime.now(timezone.utc).isoformat(),
                'reason':reason})
            self.emit('Resuming existing data after verified source compatibility: '+reason+'\n')
        self.state['source_sha256']=source
        plan=planned_scenarios();pilot=plan['episodes'][:plan['pilot_first_episodes']]
        reviewed=json.loads((Path(bundle)/'manifest.json').read_text())
        if reviewed['collection_plan']!=plan:raise PermissionError('Review collection plan does not match current plan')
        self.state['review_authorization']={'bundle':str(bundle),'manifest_sha256':file_hash(Path(bundle)/'manifest.json'),
            'approved_source_sha256':reviewed.get('source_sha256'),
            'current_source_sha256':source,'runtime_sha256':runtime,
            'reuse_approved_runtime':getattr(self.args,'reuse_approved_runtime',False),
            'note':'Original user approval preserved; exact runtime/plan compatibility required, with the audited short-rock-tile crash correction allowed.'}
        reserve=storage_reserve(plan,self.args.min_free_gb);self.state['collection_min_free_GB']=reserve
        self.save()
        current=json.loads(self.manifest.read_text())['episodes'] if self.manifest.exists() else []
        if not {e['name'] for e in current}.issubset({e['scenario']['name'] for e in plan['episodes']}):raise ValueError('Unplanned dataset episodes')
        if not self.state['milestones'].get('pilot_audit',{}).get('passed'):
            if self.collect_to(bundle,pilot,reserve,'pilot_collection') is False:return
            audit=self.audit(pilot=True)
            retained=max(0,tree_bytes(self.dataset)-audit['indexed_hdf5_bytes'])
            projected=audit['indexed_hdf5_bytes']/len(pilot)*len(plan['episodes'])*1.25+retained
            self.state['pilot_projection']={'dataset_GB_with_25_percent_margin':projected/10**9,
                'retained_attempts_and_current_overhead_GB':retained/10**9,
                'mean_episode_seconds':audit['mean_episode_seconds'],'observed_episodes':audit['episodes_total'],
                'note':'Measured balanced pilot projection; not a guarantee for later episodes.'}
            available=shutil.disk_usage(self.dataset).free+tree_bytes(self.dataset)-reserve*10**9
            if projected>min(available,self.args.max_dataset_gb*10**9):
                self.status='stopped';self.code=3;self.reason='Pilot projects insufficient storage for full dataset plus training reserves';return
        if self.collect_to(bundle,plan['episodes'],reserve,'main_collection') is False:return
        if not completion(self.manifest,plan['episodes']):raise ValueError('Complete planned dataset required before training')
        audit=self.audit()
        if shutil.disk_usage(self.dataset).free<audit['feature_cache_bytes']*1.15+self.args.min_free_gb*10**9:
            self.status='stopped';self.code=3;self.reason='Insufficient feature-cache/checkpoint space';return
        had_checkpoint=(self.checkpoints/'latest.pt').exists()
        self.train_to(bundle,min(self.args.pilot_epochs,self.args.epochs),'initial_training')
        if not had_checkpoint:self.state['milestones'].pop('policy_pilot_check',None)
        if not self.state['milestones'].get('policy_pilot_check',{}).get('passed'):
            report=self.evaluation(bundle,'policy_pilot','validation',12,stratified=True)
            check=pilot_policy_check(report);self.milestone('policy_pilot_check',check)
            if not check['passed']:
                self.status='needs_model_iteration';self.code=4;self.reason='Policy pilot failed minimum control check; inspect evaluation traces before continuing';return
        self.train_to(bundle,self.args.epochs,'remaining_training')
        self.evaluation(bundle,'final_validation','validation',120)
        final=self.evaluation(bundle,'final_test','test',120)
        self.state['final_model']={'checkpoint':str(self.checkpoints/'best.pt'),'test_success_rate':final['success_rate'],
                                  'test_outcomes':final['outcomes'],'note':'Simulation assessment only. A completed run is not deployment qualification.'}
        self.status='completed';self.code=0;self.stage='finished';self.reason='Collection, training and held-out evaluation completed'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',default='auto');parser.add_argument('--output',default=str(ROOT/'datasets/expert'))
    parser.add_argument('--no-review-export',action='store_true',help='Stop with a report if approval is missing; do not render new review videos')
    parser.add_argument('--reuse-approved-runtime',action='store_true',help='Reuse unchanged approved runtime/scenarios after training or reporting code changes; never create an approval')
    parser.add_argument('--checkpoints',default=str(ROOT/'checkpoints/production'))
    parser.add_argument('--state',default=str(ROOT/'outputs/pipeline_state.json'))
    parser.add_argument('--workers',type=int,default=64);parser.add_argument('--evaluation-workers',type=int,default=8)
    parser.add_argument('--reader-workers',type=int,default=4);parser.add_argument('--device',default='cuda')
    parser.add_argument('--epochs',type=int,default=10);parser.add_argument('--pilot-epochs',type=int,default=3)
    parser.add_argument('--patience',type=int,default=3);parser.add_argument('--min-free-gb',type=float,default=32)
    parser.add_argument('--max-dataset-gb',type=float,default=1500)
    args=parser.parse_args()
    if not 1<=args.workers<=128 or not 1<=args.evaluation_workers<=32 or not 0<=args.reader_workers<=32 or not 1<=args.pilot_epochs<=args.epochs or args.patience<0:
        parser.error('Invalid workers or epoch budget')
    if not math.isfinite(args.min_free_gb) or args.min_free_gb<32 or not math.isfinite(args.max_dataset_gb) or args.max_dataset_gb<=0:
        parser.error('At least 32 GB shutdown/training free space and a positive dataset cap are required')
    # Direct module launches also serialize the persistent state, independently
    # of the shell wrapper's VM-wide collection lock.
    if os.name!='posix':parser.error('Cloud workflow requires Linux')
    import fcntl
    state=Path(args.state).resolve();state.parent.mkdir(parents=True,exist_ok=True)
    with state.with_suffix('.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:parser.error('This pipeline state is already running')
        raise SystemExit(Pipeline(args).run())


if __name__=='__main__':main()
