"""Install and start the isolated, pinned Tidewater renderer on the Linux VM."""
import argparse,hashlib,json,os,shutil,socket,subprocess,sys,tarfile,urllib.request,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
VENDOR=ROOT/'.vendor';MAP=VENDOR/'tidewater';EXTRA=VENDOR/'tidewater-python';BROWSER=VENDOR/'tidewater-browser';RESOURCES=ROOT/'tidewater'
OUTPUT=ROOT/'outputs/tidewater_20261011'
UPSTREAM='4811ba48d795197de5621985f404e765c0b7c0ef'
NODE='node-v22.23.3-linux-x64';NODE_SHA='df450af89261115ef9f9e3830c3eeb2cc9213b63c720b1af623cb5dcbe2e02de'

def run(args,**kw):subprocess.run(list(map(str,args)),check=True,**kw)
def env():return dict(os.environ,PATH=str(VENDOR/NODE/'bin')+':'+os.environ['PATH'])

def install():
 VENDOR.mkdir(exist_ok=True);OUTPUT.mkdir(parents=True,exist_ok=True)
 if not MAP.exists():run(['git','clone','https://github.com/dgreenheck/tidewater.git',MAP])
 current=subprocess.check_output(['git','-C',str(MAP),'rev-parse','HEAD'],text=True).strip()
 if current!=UPSTREAM:
  dirty=subprocess.check_output(['git','-C',str(MAP),'status','--porcelain'],text=True).strip()
  if dirty:raise RuntimeError('Existing vendor checkout has changes; refusing to reset it')
  run(['git','-C',MAP,'checkout','--detach',UPSTREAM])
 archive=VENDOR/(NODE+'.tar.xz')
 if not archive.exists():urllib.request.urlretrieve('https://nodejs.org/dist/v22.23.3/'+archive.name,archive)
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==NODE_SHA
 if not (VENDOR/NODE).exists():
  with tarfile.open(archive) as t:t.extractall(VENDOR,filter='data')
 run(['npm','ci','--no-audit','--no-fund'],cwd=MAP,env=env())
 BROWSER.mkdir(exist_ok=True)
 if not (BROWSER/'package.json').exists():(BROWSER/'package.json').write_text(json.dumps({'private':True,'type':'module'}))
 run(['npm','install','--save-exact','playwright@1.64.0','--no-audit','--no-fund'],cwd=BROWSER,env=env())
 run(['npx','playwright','install','--with-deps','chromium'],cwd=BROWSER,env=env())
 if not (EXTRA/'cv2').exists():run([sys.executable,'-m','pip','install','--no-deps','--target',EXTRA,'opencv-python-headless==5.0.0.93'])
 patch()
 (VENDOR/'tidewater_runtime.json').write_text(json.dumps({'node_root':str((VENDOR/NODE).resolve()),'node_archive':archive.name,'node_sha256':NODE_SHA,'browser_runtime':str(BROWSER.resolve())},indent=2))

def patch():
 for name in ['src/ocean/WaterSurface.js','src/ocean/WaterQuery.js']:
  file=MAP/name;t=file.read_text()
  if 'landingWaveModule' in t:continue
  t="import { landingWaveModule } from '../landing/PhysicsWaves.js';\n"+t
  if name.endswith('WaterSurface.js'):
   t=t.replace('this.fft = fft;',"this.landingMode = new URLSearchParams(location.search).has('landing');\n\t\tthis.fft = fft;",1)
   t=t.replace('SH = !! this.shore, WK = !! this.wake','SH = !this.landingMode && !! this.shore, WK = !this.landingMode && !! this.wake',1)
   t=t.replace('disp *= waterSurface.amplitude;',"disp *= waterSurface.amplitude;\n${ this.landingMode ? 'disp = vec3f(0.0, landingWaveHeight(worldXZ), 0.0);' : '' }",1)
   t=t.replace('let jac = ( d.z + 1.0 )',"${ this.landingMode ? 'slopes = landingWaveSlope(lagXZ) + slopes * 0.025;' : '' }\n\tlet jac = ( d.z + 1.0 )",1)
   t=t.replace('deps: [ commonModule, fft.module, this.cdlod.module','deps: [ this.landingMode && landingWaveModule, commonModule, fft.module, this.cdlod.module',1)
  else:
   t=t.replace('deps: [ commonModule, fft.module, S.attenuationModule','deps: [ S.landingMode && landingWaveModule, commonModule, fft.module, S.attenuationModule',1)
   t=t.replace('return d;',"${ S.landingMode ? 'd = vec3f(0.0, landingWaveHeight(x0), 0.0);' : '' }\n\treturn d;",1)
  file.write_text(t)
 folder=MAP/'src/landing';folder.mkdir(exist_ok=True)
 for name in ['LandingBridge.js','PhysicsWaves.js']:shutil.copy2(RESOURCES/name,folder/name)
 shutil.copy2(RESOURCES/'server.mjs',BROWSER/'server.mjs')

def start():
 OUTPUT.mkdir(parents=True,exist_ok=True)
 for port in [5189,5190]:
  with socket.socket() as s:
   if s.connect_ex(('127.0.0.1',port))==0:raise RuntimeError(f'Port {port} is occupied; refusing to start another renderer')
 node=VENDOR/NODE/'bin/node';tag=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime());jobs=[]
 for name,args,cwd in [('vite',[node,MAP/'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5189'],MAP),
  ('bridge',[node,BROWSER/'server.mjs',OUTPUT],ROOT.parent)]:
  with (OUTPUT/f'{name}_{tag}.log').open('xb') as log:p=subprocess.Popen(list(map(str,args)),cwd=cwd,env=env(),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  jobs.append(dict(name=name,pid=p.pid,args=list(map(str,args))))
 (OUTPUT/f'renderer_session_{tag}.json').write_text(json.dumps(jobs,indent=2));print(json.dumps(jobs))

def stop(session):
 import psutil
 for job in json.loads(Path(session).read_text()):
  if not psutil.pid_exists(job['pid']):continue
  p=psutil.Process(job['pid']);actual=p.cmdline()
  if actual[:len(job['args'])]!=job['args']:raise RuntimeError('PID belongs to a different process; refusing to stop it')
  p.terminate();p.wait(20)

def main():
 if sys.platform!='linux':raise RuntimeError('Run this on the Linux VM; render only there')
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['install','start','stop']);p.add_argument('--session');a=p.parse_args()
 if a.mode=='install':install()
 elif a.mode=='start':start()
 else:
  if not a.session:p.error('--session is required to stop owned renderer processes')
  stop(a.session)
if __name__=='__main__':main()
