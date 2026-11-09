from pathlib import Path
R=Path(__file__).parent
s=(R/'queue_collection_v2.py').read_text().replace('search_v39','search_v46').replace('collection_v39','collection_v46').replace('expert_adapter_v39','expert_adapter_v46').replace('perception_training_v38','perception_training_v47').replace('collection_v2','collection_v3')
s=s.replace("purpose['cases_passed']==8", "purpose['cases_passed']==9\n    terminal=json.loads((ROOT/'terminal_handoff_v46/audit.json').read_text());assert terminal['status']=='passed'")
s=s.replace("name=j['name'];scenario=", "j=dict(j);j['scenario']=dict(j['scenario'])\n        if j['family']=='E10':j.update(fault=None,prefix=False);j['scenario'].update(distance=12.,initial_camera_target=True,initial_pan_deg=0.)\n        name=j['name'];scenario=")
s=s.replace("grants_training_eligibility=False)","grants_training_eligibility=False,foreground_cross_board_for_observable_pursuit=j['family']=='E10',requires_expired_memory=j['family']=='E11')")
s=s.replace("if j['fault']=='tilt':args+=['--tilt-fault']", "if j['fault']=='tilt':args+=['--tilt-fault','--fault-duration','6.0'if j['family']=='E11'else'1.6']")
s=s.replace("if j['dagger']:args+=['--mode','dagger','--prefix']", "if j['dagger']:args+=['--mode','dagger']\n                if j['prefix']:args+=['--prefix']")
s=s.replace("instance=next(i for i in range(100,108)","instance=next(i for i in range(160,168)")
compile(s,'queue_collection_v3.py','exec');(R/'queue_collection_v3.py').write_text(s)
s=(R/'harvest_collection_v2.py').read_text().replace('collection_v2','collection_v3').replace('admission_new_v2','admission_new_v3').replace('search_v39','search_v46').replace('expert_adapter_v39','expert_adapter_v46').replace('collection_v39','collection_v46');compile(s,'harvest_collection_v3.py','exec');(R/'harvest_collection_v3.py').write_text(s)
# No launch: requires full nine-flight gate AND separate healthy terminal proof.
