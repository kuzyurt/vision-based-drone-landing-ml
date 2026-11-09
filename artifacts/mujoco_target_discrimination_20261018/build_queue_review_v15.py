from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'package_review_v14.py').read_text()
s=s.replace("phase=intent.get('phase',diag.get('control_phase','unknown'))", "phase=intent.get('phase',diag.get('control_phase','unknown'))")
s=s.replace("interventions=collections.Counter();phases=collections.Counter();", "interventions=collections.Counter();phases=collections.Counter();owners=collections.Counter();takeovers=[];fault_rows=[];valid_shadow_labels=0;")
s=s.replace("  diag=row['output'].get('learner_diagnostics',{});intent=diag.get('expert_intent',{});", "  diag=row['output'].get('learner_diagnostics',{});intent=diag.get('expert_intent',diag.get('expert_shadow_intent',{}));\n  ownership=diag.get('dagger',{}).get('ownership',{});owner=diag.get('actual_command_owner',ownership.get('owner','expert'));owners[owner]+=1\n  valid_shadow_labels+=int(diag.get('dagger',{}).get('expert_label_valid',False))\n  if ownership.get('owner')=='expert' and (not takeovers or takeovers[-1]['handover_index']!=ownership['handover_index']):takeovers.append(dict(time_s=row['task_time_s'],**ownership))\n  if diag.get('evaluation_fault_active'):fault_rows.append(row['frame_index'])\n  ")
s=s.replace("unpermitted_boat_descent_rows=unsupported,", "unpermitted_boat_descent_rows=unsupported,actual_command_owners=dict(owners),takeovers=takeovers,actual_fault_rows=fault_rows,valid_shadow_label_rows=valid_shadow_labels,")
for case in ['hard','recovery','dagger']:
    name='v15_'+case
    (root/('package_review_'+name+'.py')).write_text(s.replace('v14',name))
