from pathlib import Path
R=Path(__file__).parent
for old,new in [('export_candidate_v39.py','export_candidate_v46.py'),('restore_candidate_v39.py','restore_candidate_v46.py')]:
 s=(R/old).read_text().replace('experimental_v39','experimental_v46').replace('search_v39','search_v46').replace('expert_adapter_v39','expert_adapter_v46').replace('restore_candidate_v39','restore_candidate_v46').replace('perception_training_v38','perception_training_v47').replace('Experimental V39','Experimental V46').replace('recovery.v39','recovery.v46')
 compile(s,new,'exec');(R/new).write_text(s)
