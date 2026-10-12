from pathlib import Path
import json, base64, subprocess

r = Path(__file__).resolve().parent
preview = r / 'water_fix_preview'
preview.mkdir(exist_ok=True)
browser_dir = r.parent / 'tidewater_pc_benchmark/browser'
s = (browser_dir / 'local_normal_server.mjs').read_text()
s = s.replace('5192', '5193').replace('normal_canvas_capture.webm', 'boat_water_10s.webm')
(browser_dir / 'water_preview_server.mjs').write_text(s)
s = (r / 'render_direct_normal.py').read_text()
s = s.replace("ROOT=Path(__file__).resolve().parent;OUT=ROOT/'policy_tidewater_1521_1080p_windows_normal_canvas.mp4';WEBM=ROOT/'normal_canvas_capture.webm';PKTS=ROOT/'packets.jsonl.gz';BASE='http://127.0.0.1:5192/'", "ROOT=Path(__file__).resolve().parent;OUT=ROOT/'boat_water_10s.mp4';WEBM=ROOT/'boat_water_10s.webm';PKTS=ROOT.parent/'packets.jsonl.gz';BASE='http://127.0.0.1:5193/'")
s = s.replace("ROOT/'saved_flight'", "ROOT.parent/'saved_flight'").replace('1511', '250')
s = s.replace("  rpc('render_canvas',json.loads(line));frames+=1", "  if frames >= 250: break\n  rpc('render_canvas',json.loads(line));frames+=1")
s = s.replace("summary['outcome']", "'boat-water preview only'")
s = s.replace("'-vf','setpts=N/(25*TB)'", "'-vf','setpts=N/(25*TB),tpad=stop_mode=clone:stop_duration=0.04'")
s = s.replace("'-r','25','-an'", "'-r','25','-t','10','-an'")
(preview / 'render_water_preview.py').write_text(s)

files = {name: base64.b64encode((r / 'tidewater/src' / name).read_bytes()).decode() for name in ['landing/PhysicsWaves.js', 'ocean/WaterSurface.js', 'ocean/WaterQuery.js']}
payload = base64.b64encode(json.dumps(files).encode()).decode()
remote = '''import pathlib,base64,json,shutil
root=pathlib.Path('/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/.vendor/tidewater/src')
backup=root.parent/'water_fix_originals_20261011'
files=json.loads(base64.b64decode('PAYLOAD'))
for name,data in files.items():
 p=root/name;b=backup/name;b.parent.mkdir(parents=True,exist_ok=True)
 if not b.exists():shutil.copy2(p,b)
 p.write_bytes(base64.b64decode(data))
for p in (root/'landing').glob('*Bridge.js'):
 text=p.read_text();anchor='packet.waves.forEach(';replacement='landingWaveParams.fields.enabled.value=1;'+anchor
 adjusted=text.replace("landingWaveParams.fields['c'+i].value.fromArray(c)", "landingWaveParams.fields['c'+i].value.fromArray([c[0],c[1],c[2]*Math.min(1,0.025/packet.waves.reduce((sum,w)=>sum+Math.abs(w[2]),0)),c[3]])")
 adjusted=adjusted.replace('app.shore.amplitude.value=.34;', 'app.shore.amplitude.value=.025;')
 if anchor in adjusted and replacement not in adjusted:
  b=backup/'landing'/p.name;b.parent.mkdir(parents=True,exist_ok=True)
  if not b.exists():shutil.copy2(p,b)
  p.write_text(adjusted.replace(anchor,replacement))
 elif adjusted != text:
  b=backup/'landing'/p.name;b.parent.mkdir(parents=True,exist_ok=True)
  if not b.exists():shutil.copy2(p,b)
  p.write_text(adjusted)
print('VM shared-water fix installed; originals preserved')
'''.replace('PAYLOAD', payload)
cmd = ['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=10','-i','C:/Users/gamee/.ssh/id_ed25519','hxhshsh7gyg@34.56.177.55','python3 -']
subprocess.run(cmd, input=remote.encode(), check=True, timeout=30)
print('10-second preview prepared', flush=True)
