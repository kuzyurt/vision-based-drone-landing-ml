from pathlib import Path
import json
root=Path(__file__).resolve().parent
for mode in['residual','rgb_only']:
 result=json.loads((root/('perception_training_v12_'+mode)/'result.json').read_text());v=result['validation']
 print(json.dumps(dict(mode=mode,checkpoint=result['checkpoint_sha256'],selected_epoch=result['selected_epoch'],wall_s=result['wall_s'],known=v['known_targets'],selected=v['selected_operating_point'],diagnostic=v['diagnostic_best_effort'],marker=v['selected_marker_operating_point'],gate=v['expert_gate_passed']),indent=2))
 history=json.loads((root/('perception_training_v12_'+mode)/'history.json').read_text())
 print(json.dumps(dict(mode=mode,history=[dict(epoch=r['epoch'],loss=r['loss'],known=r['known_targets'],safe=r['selected_operating_point'],diagnostic=r['diagnostic_best_effort'],marker=r['selected_marker_operating_point'])for r in history]),indent=2))
