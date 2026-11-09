from pathlib import Path
R=Path(__file__).parent
s=(R/'render_static_repair_v44b.py').read_text().replace('static_repair_v44b','static_repair_v52')
s=s.replace("cache=proof['models']['hard']", "cache=proof['models'][job['model_scope']]")
a="subjects=['target']*6+[n for n in groups if n!='target']+['background']*2"
b="subjects=['target']*6+['decoy_dark']*8+['decoy_similar']*4+(['decoy_false_cross_board']*2 if 'decoy_false_cross_board'in groups else[])+[n for n in groups if n not in ['target','decoy_dark','decoy_similar','decoy_false_cross_board']]+['background']*2"
assert a in s;s=s.replace(a,b);compile(s,'render_static_repair_v52.py','exec');(R/'render_static_repair_v52.py').write_text(s)
s=(R/'queue_static_repair_v44b.py').read_text().replace('static_repair_v44b','static_repair_v52')
a=s.index('            jobs.append(');b=s.index('    assert len(jobs)',a)
s=s[:a]+'''            for model_index,model_scope in enumerate(['basic','hard']):
                jobs.append(dict(**w,name=f"{w['role']}_{w['kind']}_{model_scope}_palette{palette}",frames=96 if w['role']=='training'else 80,seed=w['world_seed']+400000+100*model_index+palette,palette=palette,model_scope=model_scope,rotation=[0.,37.,89.,153.,225.][i//2]))
'''+s[b:]
s=s.replace('len(jobs)==35','len(jobs)==70').replace("sum(j['frames']for j in jobs)==3200","sum(j['frames']for j in jobs)==6400");compile(s,'queue_static_repair_v52.py','exec');(R/'queue_static_repair_v52.py').write_text(s)
s=(R/'launch_static_repair_v44b.py').read_text().replace('static_repair_v44b','static_repair_v52');compile(s,'launch_static_repair_v52.py','exec');(R/'launch_static_repair_v52.py').write_text(s)
(R/'PERCEPTION_REPAIR_V52_SUBPLAN.md').write_text('''# Bounded follow-up from CLOSED known-development evidence,08:30UTC

Observed: V46mid/far physically stopped100s. Actual target tracks already had
3+objectness confirmations153/159mid and205/211far; additional scan dwell or
objectness threshold relaxation is therefore NOT supported and NOT implemented.
All six strong mid target-ID assertions were on actual decoy_dark, none on target.
Current static training used ONLY hard cached scene; native failures use basic.
Do not train on failed raw or copy its poses. No unknown/clone labels invented.

1. Independently render6400fresh random static images across basic AND hard CAD,
five maps/palettes and disjoint role worlds. Increase dark/similar-boat coverage.
Same-camera segmentation labels offline only, marker-hidden target same design,
contact images excluded, no PX4/action/teacher trajectories. Eight total workers
including all native workers,4GiB/1GiBreserves. Stop on infrastructure failure.
2. Build exact-hash-bound RGB-only verifier cache, inspect actual RGB labels first.
3. At most8epochs, V47initializer, immutable detector/backbone/pose/spatial,
old TRAINING-only KL rehearsal plus wide/close/current fresh GT. Keep separate
validation groups, zero false assertions in all, wide>=75/152(anchored original
V38 78 with original<=2pp allowance), close recall>=.272; no confidence changes.
No blind extensions or failed-raw supervision. Candidate absent if gates fail.
4. Camera survey integration correction ONLY if source/closed trace proof holds:
existing negative-feedback 'start new survey' must call actual elevation survey
transition, preserving completed360 semantics. First far counterfactual task38.2s;
no physical improvement claim before actual matched native development checks.
5. Freeze/export/verify local new checkpoint before native development tests.
Actual purpose gates still block bulk data. No production install, no Tidewater
training. Original cutoff unchanged; deliverytarget13:00UTC. Reduce episode count
or omit unfinished benchmarks rather than relax gates. Log actual timing.
''')
