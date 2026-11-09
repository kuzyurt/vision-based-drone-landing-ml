from pathlib import Path
import collections,hashlib,json,tarfile
r=Path(__file__).resolve().parent
archive=r/'compact_results.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f8f2032c449388a363561902e8464babacc8781befcfc3c5ea66423c4a68523d'
out=r/'verified';assert not out.exists();out.mkdir()
with tarfile.open(archive)as t:
    for member in t.getmembers():assert(out/member.name).resolve().is_relative_to(out.resolve())
    t.extractall(out,filter='data')
manifest=json.loads((out/'download_manifest.json').read_text())
for name,h in manifest.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h,name
result=json.loads((out/'audited_results.json').read_text())
assert result['new_tests']==result['measured']==26 and result['boat_landings']==5 and result['collisions']==0
print('Verified',len(manifest),'files;26measured,5landings,0registeredcollisions')
for x in result['results']:
    print(json.dumps(dict(id=x['id'],landed=x['landed'],s=round(x['flight_seconds'],3),
        speed=round(x['final_2s_speed_m_s']['mean'],4),metric_frames=x['metric_frames'],
        min_body_height=round(x['minimum_recorded_true_body_height_m'],3),
        phases=x['phases'],radio_frames=x['radio_available_frames'],frames=x['frames'])))
print('GLOBAL_MAX_COMMAND',max(x['max_command_xy_m_s']for x in result['results']))
