"""Prepare conditional queue only; never bypasses actual eight-purpose gate."""
from pathlib import Path
p=Path(__file__).parent
s=(p/'queue_collection_v1.py').read_text().replace("search_v35/sources","search_v39/sources").replace("search_v35/audit_v36","search_v39/audit").replace("search_v35/runtime_probe.json","search_v39/runtime_probe.json").replace("collection_v1","collection_v2").replace('harvest_collection_v1.py','harvest_collection_v2.py').replace('run_semantic_collection_v35.py','run_semantic_collection_v39.py').replace("'EXPERT_RECOGNIZER_ROOT':'perception_training_v12_rgb_only'","'EXPERT_RECOGNIZER_ROOT':'approved_curriculum_20261020/perception_training_v38'")
s=s.replace("    assert purpose['status']=='passed'and purpose['cases_passed']==8","    assert purpose['status']=='passed'and purpose['cases_passed']==8\n    binding=json.loads((ROOT/'search_v39/candidate_binding.json').read_text());assert sha(binding['checkpoint'])==binding['recognizer_sha256']==purpose['recognizer_sha256']")
(p/'queue_collection_v2.py').write_text(s)
s=(p/'harvest_collection_v1.py').read_text().replace("collection_v1","collection_v2").replace('admission_new_v1','admission_new_v2').replace('audit_semantic_pilots_v3.py','audit_semantic_pilots_v4.py').replace('search_v35/sources','search_v39/sources').replace('expert_adapter_v35.py','expert_adapter_v39.py').replace('run_semantic_collection_v35.py','run_semantic_collection_v39.py')
s=s.replace("a.EXPECTED_HARNESS=sha(src/'run_semantic_collection_v39.py')","a.EXPECTED_HARNESS=sha(src/'run_semantic_collection_v39.py');binding=json.loads((ROOT/'search_v39/candidate_binding.json').read_text());a.EXPECTED_RECOGNIZER=binding['recognizer_sha256'];assert sha(binding['checkpoint'])==a.EXPECTED_RECOGNIZER")
(p/'harvest_collection_v2.py').write_text(s)
for n in ['queue_collection_v2.py','harvest_collection_v2.py']:compile((p/n).read_text(),n,'exec')
