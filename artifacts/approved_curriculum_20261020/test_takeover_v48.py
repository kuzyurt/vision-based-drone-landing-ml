from pathlib import Path
import hashlib,json,sys,types
R=Path(__file__).parent;S=R/'search_v48/sources';sys.path.insert(0,str(S))
from target_learning.takeover import Evidence
from target_learning.takeover_v48 import StruggleTakeover

def run(kind):
 s=StruggleTakeover();first=None
 for k in range(300):
  t=k*.04;confirmed=kind in ['confirmed','identity_without_landing_permission'];velocity=0.if kind=='hover'else .2 if kind=='ascending'else-.3
  e=Evidence(t,.04,True,True,confirmed,False,None,None,None,True,True,False,False,frame_id=1 if kind=='repeat'else k)
  obs={'px4':{'armed':True,'landed':False,'position_enu_m':[0,0,6-.3*t],'velocity_enu_m_s':[0,0,velocity]}}
  s.update_context({'metric_confirmed':True,'metric_age_s':.04},{'metric_confirmed':confirmed,'expert_intent':{'allow_descent':kind=='confirmed'}},obs,[0,0,.3,0,0,0],False);d=s.step(e)
  if d.owner!='policy':first=(t,d.reason,s.struggle_evidence);break
 return first
results={k:run(k)for k in ['descent','confirmed','identity_without_landing_permission','hover','ascending','repeat']}
assert results['descent']and results['descent'][0]>=5.3
assert results['identity_without_landing_permission']and results['identity_without_landing_permission'][0]>=5.3
assert all(results[k]is None for k in ['confirmed','hover','ascending','repeat'])
assert 'target_learning.dagger_v48'in(S/'run_semantic_collection_v48.py').read_text()
receipt=dict(status='passed',tests=results,source_hashes={n:hashlib.sha256((S/'target_learning'/n).read_bytes()).hexdigest()for n in ['takeover_v48.py','unverified_descent_v48.py','dagger_v48.py']},not_physical_rescue_proof=True)
(R/'search_v48/source_test_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
