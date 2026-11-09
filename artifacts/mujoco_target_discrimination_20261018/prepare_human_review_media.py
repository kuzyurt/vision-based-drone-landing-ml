from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'export_actual_review_v13.py').read_text()
s=s.replace("p.add_argument('--max-seconds',type=float,default=30.);a=p.parse_args();", "p.add_argument('--task-start',type=float,required=True);p.add_argument('--task-end',type=float,required=True)\n    p.add_argument('--max-seconds',type=float,default=30.);a=p.parse_args();")
s=s.replace("rows=[r for r in rows if 'observation'in r];assert rows", "rows=[r for r in rows if 'observation'in r and a.task_start<=r['task_time_s']<=a.task_end];assert rows")
(root/'export_actual_review_window.py').write_text(s)
s=(root/'audit_actual_v16_fault.py').read_text().replace('v16','v17')
s=s.replace("['gimbal_rad'][0]","['gimbal_rad'][1]")
s=s.replace("['previous_executed_action'][4]","['previous_executed_action'][5]")
s=s.replace('executed_pan_rate','executed_tilt_rate').replace('observed_pan_change','observed_tilt_change')
s=s.replace("' / pan '","' / tilt '")
s=s.replace("pan {math.degrees", "tilt {math.degrees")
s=s.replace("result=dict(actual_active_frames", "heights=[r['observation']['px4']['position_enu_m'][2]for r in rows[lo:hi+251]]\nresult=dict(height_at_fault_m=heights[0],maximum_height_next10s_m=max(heights),observed_height_gain_m=max(heights)-heights[0],actual_active_frames")
(root/'audit_actual_v17_fault.py').write_text(s)
