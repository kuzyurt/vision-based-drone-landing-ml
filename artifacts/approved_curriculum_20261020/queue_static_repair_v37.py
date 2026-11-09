"""Eight bounded static rendering workers, fixed split before first image."""
from pathlib import Path
import datetime,hashlib,json,os,select,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'static_repair_v37'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2));t.replace(p)
def main():
    OUT.mkdir(exist_ok=False);proof=json.loads((ROOT/'world_contract_v1/proof.json').read_text());jobs=[]
    for i,w in enumerate(proof['worlds']):jobs.append(dict(**w,name=f"{w['role']}_{w['kind']}",frames=96 if w['role']=='training'else 48,seed=w['world_seed']+50000,rotation=[0.,37.,89.,153.,225.][i//2]))
    assert len(jobs)==10 and sum(j['frames']for j in jobs)==720
    plan=dict(schema='approved.static.repair-plan.v36',jobs=jobs,maximum_workers=8,worker_source_sha256=sha(ROOT/'render_static_repair_v37.py'),world_contract_sha256=sha(ROOT/'world_contract_v1/proof.json'),teacher_actions=False,production_qualification=False);save(OUT/'plan.json',plan)
    for j in jobs:save(OUT/(j['name']+'_job.json'),j)
    queue=jobs.copy();active={};closed=[];begin=time.monotonic()
    def state():save(OUT/'state.json',dict(status='running'if active or queue else'completed',active={str(k):v['job']['name']for k,v in active.items()},queued=len(queue),closed=closed,elapsed_s=time.monotonic()-begin))
    while active or queue:
        available=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))/1024**2
        free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).splitlines()[0])/1024
        # Other native rendering jobs count toward the same total of eight.
        running=subprocess.check_output(['ps','-u',str(os.getuid()),'-o','args='],text=True).splitlines();native=sum('run_semantic_collection_'in x and '--scenario-file'in x for x in running)
        while queue and len(active)+native<8 and available>6.84 and free>1.5:
            j=queue.pop(0);log=(OUT/(j['name']+'.log')).open('x');p=subprocess.Popen([sys.executable,str(ROOT/'render_static_repair_v37.py'),'--job',str(OUT/(j['name']+'_job.json'))],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL);active[p.pid]=dict(p=p,job=j,log=log);available-=2.84;free-=.1
        state()
        if active:
            fds=[os.pidfd_open(pid)for pid in active];select.select(fds,[],[],30)
            for fd in fds:os.close(fd)
        else:time.sleep(10)
        for pid,v in list(active.items()):
            if v['p'].poll()is None:continue
            v['log'].close();code=v['p'].returncode;receipt=OUT/v['job']['name']/'receipt.json';closed.append(dict(name=v['job']['name'],returncode=code,receipt=str(receipt)));del active[pid]
            if code!=0 or not receipt.exists():
                for q in active.values():q['p'].terminate()
                save(OUT/'state.json',dict(status='failed_specific_worker',failed=closed[-1],closed=closed));raise RuntimeError(str(closed[-1]))
    state()
    entries=[json.loads((OUT/j['name']/'receipt.json').read_text())for j in jobs]
    save(OUT/'manifest.json',dict(status='completed',entries=entries,plan_sha256=sha(OUT/'plan.json'),frames=sum(x['frames']for x in entries),teacher_actions=False,elapsed_s=time.monotonic()-begin))
if __name__=='__main__':main()
