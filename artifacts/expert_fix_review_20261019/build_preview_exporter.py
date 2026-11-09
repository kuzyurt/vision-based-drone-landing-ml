from pathlib import Path
import subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent/'mujoco_target_discrimination_20261018'
s=(ROOT/'export_actual_review_v13.py').read_text()
s=s.replace("p.add_argument('--max-seconds',type=float,default=30.);a=p.parse_args();", "p.add_argument('--start-task',type=float);p.add_argument('--end-task',type=float);p.add_argument('--max-seconds',type=float,default=30.);a=p.parse_args();")
s=s.replace("    rows=[r for r in rows if 'observation'in r];assert rows", "    rows=[r for r in rows if 'observation'in r and(a.start_task is None or r['task_time_s']>=a.start_task)and(a.end_task is None or r['task_time_s']<=a.end_task)];assert rows")
s=s.replace('OBSERVABLE EXPERT — REVIEW PREVIEW','REPLACEMENT EXPERT — PENDING USER REVIEW')
s=s.replace("f'No radio | actual cameras | {speed:.2f}x | recognition NOT qualified; not learner success'", "f'No radio | actual cameras | {speed:.2f}x | review only, not approved training data'")
s=s.replace("owner=diag.get('dagger',{}).get('ownership',{}).get('owner','expert')", "owner=diag.get('actual_command_owner',diag.get('dagger',{}).get('ownership',{}).get('owner','expert'))")
s=s.replace("f'Own altitude {pos[2]:.2f}m ENU | image age {row[\"observation\"][\"image_age_s\"]:.3f}s'", "f'Altitude {pos[2]:.2f}m | image age {row[\"observation\"][\"image_age_s\"]:.3f}s | native {diag.get(\"control_phase\")}'")
s=s.replace("draw.text((24,654),'Check: scan/inspect choices, wrong-object rejection, camera aim, descent and recovery.',font=small,fill='#a8c4d6')", "draw.text((24,654),f'Pan/tilt {row[\"observation\"][\"gimbal_rad\"][0]*180/math.pi:.1f}/{row[\"observation\"][\"gimbal_rad\"][1]*180/math.pi:.1f} deg | {intent.get(\"reason\",\"\")} ',font=small,fill='#a8c4d6')")
s=s.replace("report=dict(source_episode=str(directory)","report=dict(first_task_s=rows[0]['task_time_s'],last_task_s=rows[-1]['task_time_s'],training_eligible=False,source_episode=str(directory)")
compile(s,'export_replacement_preview.py','exec');p=ROOT/'export_replacement_preview.py';assert not p.exists();p.write_text(s)
subprocess.run([sys.executable,str(ROOT/'vm_io.py'),'push',p.name],check=True)
