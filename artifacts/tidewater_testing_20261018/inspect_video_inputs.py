from pathlib import Path
import json,psutil,shutil,subprocess
subprocess.run(['whoami']);subprocess.run(['hostname'])
root=Path(__file__).resolve().parent
current=root/'tidewater_limits_20261018T153300Z'
assert json.loads((current/'state.json').read_text())['status']=='completed'
print('active_render_or_test_processes',[(p.info['pid'],p.info['name'])for p in psutil.process_iter(['pid','name','cmdline'])if p.info['name']=='ffmpeg'or any(a.endswith('/tidewater_speed_suite_20261018.mjs')for a in(p.info['cmdline']or[]))])
print('ffmpeg',shutil.which('ffmpeg'),'ffprobe',shutil.which('ffprobe'))
support=subprocess.run(['ffmpeg','-hide_banner','-h','encoder=libx264'],capture_output=True,text=True)
print('x264_available','Encoder libx264'in support.stdout)
print('font',Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').is_file())
for group,name in [('tidewater_limits_20261018T153300Z','visible_0p6_visual'),('tidewater_limits_20261018T153300Z','visible_1p4_radio'),('tidewater_speed_20261018T152500Z','far20_cloudy_visual')]:
    p=root/group/'cases'/name
    report=json.loads((p/'report.json').read_text());images=sorted(p.glob('camera-*.png'))
    print(json.dumps(dict(name=name,images=len(images),first=images[0].name,last=images[-1].name,outcome=report['physical_assessment'],seconds=report['flight_seconds'])))
