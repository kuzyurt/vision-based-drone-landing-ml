from pathlib import Path
import transport
for script in ['inspect_static_v52.py','encode_rescue_v48.py']:
 try:print(transport.run(script))
 except Exception as e:print(getattr(e,'stderr',str(e)));raise
D=Path(__file__).parent/'vm_results';transport.pull('static_repair_v52/basic_hard_actual_labels.jpg',D/'v52_basic_hard_actual_labels.jpg');transport.pull('roi_cache/static_v52/actual_static_labels.jpg',D/'v52_actual_static_labels.jpg')
