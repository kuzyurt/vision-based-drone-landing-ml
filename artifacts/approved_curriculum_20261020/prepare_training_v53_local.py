from pathlib import Path
R=Path(__file__).parent
s=(R/'train_static_verifier_v47.py').read_text().replace("DATA=ROOT/'static_repair_v44b';OUT=ROOT/'perception_training_v47'","DATA=ROOT/'static_repair_v52';OUT=ROOT/'perception_training_v53'").replace("PARENT=ROOT/'perception_training_v38/best.pt'","PARENT=ROOT/'perception_training_v47/best.pt'").replace('roi_cache/static_v44b','roi_cache/static_v52').replace("manifest['frames']==3200","manifest['frames']==6400").replace('52f1c07a09aa781889d6187dab4817047526b0c24234b6ef245920fd709ad588','fd12bb896037b928fdb88a10a76ab1a0038538d6624042afe8788f0a1ffd19ff')
s=s.replace("old=load_cache(ROOT/'roi_cache/static_v38');model=", "old=load_cache(ROOT/'roi_cache/static_v38');close=load_cache(ROOT/'roi_cache/static_v44b');old['training']={n:np.concatenate([old['training'][n],close['training'][n]])for n in ['rgb','meta','classes','marker','mask']};model=")
s=s.replace("groups={'new_close':fresh['validation'],'wide_rehearsal':old['validation']}","groups={'new_negatives':fresh['validation'],'new_close':close['validation'],'wide_rehearsal':old['validation']}")
s=s.replace("for k in ['static_v44b','static_v38']","for k in ['static_v52','static_v44b','static_v38']")
s=s.replace("for k in ['static_v52','static_v38']","for k in ['static_v52','static_v44b','static_v38']")
s=s.replace("best=float('inf')","best=sum(v['score']for v in baseline.values())")
s=s.replace("metrics['wide_rehearsal']['selected_operating_point']['target_recall']>=baseline['wide_rehearsal']['selected_operating_point']['target_recall']-.02", "metrics['wide_rehearsal']['selected_operating_point']['target_recall']>=75/152")
s=s.replace("and (false(baseline['new_close'])==0 or false(metrics['new_close'])<false(baseline['new_close']))", "and metrics['new_negatives']['selected_operating_point']['target_recall']>=baseline['new_negatives']['selected_operating_point']['target_recall']-.02 and (false(baseline['new_negatives'])==0 or false(metrics['new_negatives'])<false(baseline['new_negatives']))")
s=s.replace("wide recall >= baseline minus .02", "wide recall >=75/152 anchored to originalV38 allowance; close/new-negative recall >= respective baseline minus .02")
compile(s,'train_static_verifier_v53.py','exec');(R/'train_static_verifier_v53.py').write_text(s)
for old,new in [('queue_cache_v45.py','queue_cache_v53.py'),('launch_cache_v45.py','launch_cache_v53.py')]:
 s=(R/old).read_text().replace('static_repair_v44b','static_repair_v52').replace('static_cache_v45','static_cache_v53').replace('queue_cache_v45','queue_cache_v53').replace('train_static_verifier_v45','train_static_verifier_v53');compile(s,new,'exec');(R/new).write_text(s)
