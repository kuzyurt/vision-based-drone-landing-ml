from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,time
r=Path(__file__).resolve().parent;out=r/'failure_videos';out.mkdir()
base='hxhshsh7gyg@34.87.180.165:/home/hxhshsh7gyg/vision-based-drone-landing-ml/landing_training/outputs/landing_hardening_20261018T011610Z/tidewater_failure_videos_20261018_v2/'
names=['01_no_radio_visible_start.mp4','02_radio_faster_boat.mp4','03_no_radio_distant_cloudy.mp4',
    '01_no_radio_visible_start_preview.jpg','02_radio_faster_boat_preview.jpg','03_no_radio_distant_cloudy_preview.jpg','manifest.json']
command=[shutil.which('scp'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/Users/gamee/.ssh/id_ed25519']
command +=[base+name for name in names]+[str(out)]
started=time.monotonic()
with(r/'failure_video_download.log').open('x')as log:
    subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=290,check=True)
elapsed=time.monotonic()-started
manifest=json.loads((out/'manifest.json').read_text())
for row in manifest['videos']:
    path=out/row['file'];assert path.stat().st_size==row['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    assert row['video_seconds']==24 and row['actual_recorded_images']==44
receipt=dict(status='downloaded_and_hash_verified',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    download_seconds=elapsed,total_bytes=sum((out/name).stat().st_size for name in names),
    under_five_minutes=elapsed<300,original_recorded_timelapse=True,simulation_rerun=False,
    files=[str(out/row['file'])for row in manifest['videos']])
(out/'download_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
