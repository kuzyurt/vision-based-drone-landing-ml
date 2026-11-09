from pathlib import Path
import transport
R=Path(__file__).parent;D=R/'vm_results';D.mkdir(exist_ok=True)
for name in ['search_v48/audit/learner_struggle_audit.json','search_v48/audit/learner_struggle_actual_rgb.jpg','search_v46/audit/search_mid_actual_rgb.jpg','search_v46/audit/search_far_actual_rgb.jpg']:
 dest=D/('v48_'+Path(name).name if 'v48'in name else 'v46_'+Path(name).name);transport.pull(name,dest);print(dest)
