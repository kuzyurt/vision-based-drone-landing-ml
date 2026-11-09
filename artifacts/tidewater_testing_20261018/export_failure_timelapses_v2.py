"""Encode actual sparse onboard recordings on the VM; no simulation or reconstructed frames."""
from pathlib import Path
import datetime,hashlib,json,subprocess,time
root=Path(__file__).resolve().parent
out=root/'tidewater_failure_videos_20261018_v2';assert not out.exists();out.mkdir()
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
phases={'visual_search':'Searching','visual_acquire':'Approaching visual candidate',
 'visual_reacquire':'Reacquiring','visual_attention':'Camera attention',
 'recovery_climb':'Recovery climb','recovery_scan':'Recovery scan'}
cases=[
 ('tidewater_limits_20261018T153300Z','visible_0p6_visual','01_no_radio_visible_start',
  '1. No radio | boat about 0.64 m/s | initially visible boat'),
 ('tidewater_limits_20261018T153300Z','visible_1p4_radio','02_radio_faster_boat',
  '2. Radio enabled | boat about 1.35 m/s | initially visible boat'),
 ('tidewater_speed_20261018T152500Z','far20_cloudy_visual','03_no_radio_distant_cloudy',
  '3. No radio | 21 m start | cloudy, wind, camera initially looking away')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(seconds):
    cs=round(seconds*100);return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'
def dialogue(start,end,style,text):return f'Dialogue: 0,{stamp(start)},{stamp(end)},{style},,0,0,0,,{text}\n'
records=[];began=time.monotonic()
for group,name,label,title in cases:
    folder=root/group/'cases'/name
    report=json.loads((folder/'report.json').read_text());assert not report['physical_assessment']['landed']
    images=sorted(folder.glob('camera-*.png'));assert len(images)>=10
    indices={int(p.stem.split('-')[-1]):p for p in images};rows={}
    for line in(folder/'steps.jsonl').open():
        row=json.loads(line)
        if row['frame']in indices:rows[row['frame']]=row
    assert len(rows)==len(images)
    duration=len(images)*.5+2
    source=[];ass='''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 816
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,DejaVu Sans,23,&H00FFFFFF,&H000000FF,&H0010141C,&H0010141C,0,0,0,0,100,100,0,0,1,1,0,8,12,12,11,1
Style: Caption,DejaVu Sans,19,&H00FFFFFF,&H000000FF,&H0010141C,&H0010141C,0,0,0,0,100,100,0,0,1,1,0,2,10,10,7,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    ass+=dialogue(0,duration,'Title',title)
    listing=[]
    for i,image in enumerate(images):
        index=int(image.stem.split('-')[-1]);row=rows[index];o=row['observation'];d=row['result']['diagnostics']
        task=float(o['mission']['elapsed_s']);phase=phases.get(d['control_phase'],d['control_phase'].replace('_',' '))
        radio='OFF'if not report['radio']else'packet valid'if o['beacon']['valid']else'packet unavailable'
        caption=f'Flight t={task:.1f}s | {phase} | accepted pad pose: '+('YES'if d['metric_valid']else'NO')+' | Radio: '+radio
        caption+=r'\N'+'TIME-LAPSE: actual recorded camera images, about 4 s apart; shown 0.5 s each. No reconstruction.'
        ass+=dialogue(i*.5,(i+1)*.5,'Caption',caption)
        listing.extend(["file '"+str(image)+"'",'duration 0.5'])
        source.append(dict(file=str(image.relative_to(root)),sha256=sha(image),frame=index,task_seconds=task,phase=d['control_phase']))
    listing.extend(["file '"+str(images[-1])+"'",'duration 2',"file '"+str(images[-1])+"'"])
    ass+=dialogue(len(images)*.5,duration,'Caption',
        f"Recorded outcome: NO BOAT LANDING; manual hold at {report['flight_seconds']:.1f}s"+r'\N'+'Last captured image held. The final seconds between snapshots were not recorded as images.')
    concat=out/(label+'.concat');concat.write_text('\n'.join(listing)+'\n')
    subtitles=out/(label+'.ass');subtitles.write_text(ass)
    video=out/(label+'.mp4')
    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-f','concat','-safe','0','-i',str(concat),
        '-vf','scale=1280:720:flags=bilinear,pad=1280:816:0:48:color=0x10141c,tpad=stop_mode=clone:stop_duration=3,fps=25,ass='+str(subtitles),
        '-t',str(duration),'-r','25','-an','-c:v','libx264','-preset','veryfast','-crf','21','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    subprocess.run(command,check=True,timeout=90)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,nb_frames','-of','json',str(video)]))
    assert abs(float(probe['format']['duration'])-duration)<.1 and probe['streams'][0]['codec_name']=='h264'
    preview=out/(label+'_preview.jpg')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-ss','0.1','-i',str(video),'-frames:v','1',str(preview)],check=True,timeout=15)
    record=dict(file=video.name,sha256=sha(video),bytes=video.stat().st_size,probe=probe,
        case=name,original_flight_seconds=report['flight_seconds'],source_camera_resolution=[640,360],
        actual_recorded_images=len(images),video_seconds=duration,actual_source_images=source,
        interpretation='Actual onboard image time-lapse; sparse recorded frames, no reconstructed or re-simulated frames.',report_sha256=sha(folder/'report.json'))
    records.append(record)
manifest=dict(status='exported_actual_recorded_failure_timelapses',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    encoding_wall_seconds=time.monotonic()-began,simulation_rerun=False,new_scene_render=False,VM_encoding_only=True,videos=records)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(folder=str(out),encoding_seconds=manifest['encoding_wall_seconds'],files=[dict(file=x['file'],bytes=x['bytes'],sha256=x['sha256'],duration=x['video_seconds'])for x in records]),indent=2))
