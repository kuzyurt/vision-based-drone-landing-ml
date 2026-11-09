"""Closed public-state contradictions only; no model fitting or action outputs."""
from pathlib import Path
import json
R=Path(__file__).parent;report={}
for name in ['search_mid','search_far']:
 c=R/'search_v46/pilots'/name
 assert (c/'preview_result.json').exists(),'Wait for closed native evidence'
 rows=[json.loads(x)for x in(c/'steps.jsonl').open()];dangling=[];retired=[];bands={};phases={};xy=[]
 for r in rows:
  d=r['output'].get('learner_diagnostics')or{};intent=d.get('expert_intent')or{};phase=intent.get('phase');phases[phase]=phases.get(phase,0)+1;band=str(d.get('expert_scan_band'));bands[band]=bands.get(band,0)+1;xy.append(r['observation']['px4']['position_enu_m'][:2]);fb=d.get('inspection_feedback')or{}
  age=d.get('metric_age_s');good=bool(d.get('metric_confirmed')and age is not None and age<=.16 and d.get('metric_uncertainty_m',999)<=.15)
  if d.get('expert_observable_target_confirmed')and intent.get('selected_track')is None and not good and phase not in ['local_downlook','recovery_climb','recovery_downlook','target_contact_confirmation']:dangling.append(dict(task_s=r.get('task_time_s'),phase=phase,feedback=fb))
  if fb.get('retired'):retired.append(dict(task_s=r.get('task_time_s'),feedback=fb,ID_after=d.get('expert_observable_target_confirmed'),selected_after=intent.get('selected_track'),metric_good=good))
 report[name]=dict(outcome=json.loads((c/'preview_result.json').read_text())['outcome'],rows=len(rows),dangling_confirmed_no_selected_no_geometry_frames=len(dangling),examples=dangling[:8],retired=retired,bands=bands,phases=phases,net_xy_m=((xy[-1][0]-xy[0][0])**2+(xy[-1][1]-xy[0][1])**2)**.5)
(R/'search_v46/closed_public_invariants.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
