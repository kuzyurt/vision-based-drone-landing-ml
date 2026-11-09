"""Only module startup and IPC; not a flight, estimator, or parity certificate."""
from pathlib import Path
import datetime,json,subprocess,time
R=Path(__file__).resolve().parent;REPO=R.parents[1]

def main():
    out=R/'px4_bridge_probe_v1';out.mkdir(exist_ok=False)
    with(out/'stderr.log').open('x')as log:
        p=subprocess.Popen(['node',str(R/'px4_windows_bridge.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            hello=json.loads(p.stdout.readline());assert hello['status']=='bridge_ready'
            parameters=json.loads((REPO/'tidewater-game/app/public/landing/physics/configuration.json').read_text())['parameters']
            def rpc(n,op,**kw):
                p.stdin.write(json.dumps(dict(id=n,op=op,**kw))+'\n');p.stdin.flush();reply=json.loads(p.stdout.readline());assert reply.get('ok'),reply;return reply
            init=rpc(1,'initialize',parameters=parameters);reply=rpc(2,'poll',minimum_time=0)
            assert len(reply['observation'])==20 and len(reply['actuators'])==19
            rpc(3,'dispose');p.wait(timeout=8)
            result=dict(status='pinned_PX4_Windows_Node_load_and_IPC_passed',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),px4_revision=init['px4_revision'],hello=hello,startup_complete=reply['startup_complete'],flight=False,estimator_qualification=False,linux_used=False,Tidewater_world_or_images_used=False)
            (out/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
        finally:
            if p.poll()is None:p.terminate();p.wait(timeout=8)
            p.stdin.close();p.stdout.close()

if __name__=='__main__':main()
