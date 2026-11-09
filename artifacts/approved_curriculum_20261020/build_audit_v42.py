from pathlib import Path
p=Path(__file__).parent;s=(p/'audit_gate_v39.py').read_text().replace('search_v39','search_v42').replace('expert_adapter_v39','expert_adapter_v42').replace('run_semantic_collection_v39','run_semantic_collection_v42').replace('P02_v39_actual_purpose','P02_v42_actual_purpose')
s=s.replace("'tilt_loss','learner_struggle']:","'tilt_loss','learner_struggle','expired_memory']:")
s=s.replace("        results.append(result);",'''        if name in ['learner_struggle','expired_memory'] and(case/'steps.jsonl').exists():
            rows=[json.loads(x)for x in(case/'steps.jsonl').open()];transitions=[];previous=None;latched=False;latched_ok=True;expired=0;policy=0
            for i,row in enumerate(rows):
                d=row['output'].get('learner_diagnostics')or{};owner=d.get('actual_command_owner');dg=d.get('dagger')or{};policy+=owner=='policy'
                if owner=='expert'and previous=='policy':
                    transitions.append(dict(frame=i,task_s=row.get('task_time_s'),ownership=dg.get('ownership'),struggle=dg.get('struggle_evidence'),learner_wrong_observed=dg.get('wrong_candidate_selected_by_learner')));latched=True
                if latched and owner=='policy':latched_ok=False
                if owner=='expert'and d.get('expert_expired_memory_downlook'):expired+=1
                if owner not in ['evaluation_fault']:previous=owner
            def genuine(t):
                o=t.get('ownership')or{};e=t.get('struggle')or{};reason=o.get('reason','')
                return ((reason=='sustained_observed_wrong_object_pursuit'and e.get('wrong_pursuit_duration_s',0)>=3.)or(reason=='sustained_loss_after_learner_acquisition'and e.get('loss_duration_s',0)>=6. and not e.get('learner_recovery_progressing'))or(reason=='repeated_learner_acquire_loss_cycle'and e.get('loss_events_last20s',0)>=2 and not e.get('learner_recovery_progressing'))or(reason=='near_deck_learner_cannot_establish_geometry'and e.get('near_deck_missing_geometry_s',0)>=3.))
            checks=result.setdefault('checks',[]);checks.append(dict(name='genuine observable struggle and latched expert rescue, no preventive takeover',passed=policy>0 and bool(transitions)and all(genuine(t)for t in transitions)and latched_ok,detail=dict(policy_rows=policy,transitions=transitions,latched=latched_ok)))
            if name=='learner_struggle':
                first=json.loads((case/'initial_view_receipt.json').read_text());checks.append(dict(name='natural actual learner start, visible foreground copied-cross board',passed=first.get('foreground_board_pixels',0)>=32 and not any((r['output'].get('learner_diagnostics')or{}).get('actual_command_owner')=='expert_prefix'for r in rows),detail=first.get('foreground_board_pixels')))
            if name=='expired_memory':checks.append(dict(name='actual post-takeover expired-memory camera path',passed=expired>0,detail=expired))
            result['rescue_semantics']=dict(transitions=transitions,expired_memory_expert_frames=expired);result['status']='passed'if all(x['passed']for x in checks)else'failed'
        results.append(result);''')
s=s.replace("passed==8 else'failed'","passed==9 else'failed'").replace('cases_total=8','cases_total=9').replace('total=8','total=9')
(p/'audit_gate_v42.py').write_text(s)
(p/'launch_audit_v42.py').write_text((p/'launch_audit_v39.py').read_text().replace('search_v39','search_v42').replace('audit_gate_v39','audit_gate_v42'))
for n in ['audit_gate_v42.py','launch_audit_v42.py']:compile((p/n).read_text(),n,'exec')
