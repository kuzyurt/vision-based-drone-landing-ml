from pathlib import Path
R=Path(__file__).parent;s=(R/'train_static_verifier_v45.py').read_text();s=s.replace("OUT=ROOT/'perception_training_v45'","OUT=ROOT/'perception_training_v47'")
s=s.replace("lr=5e-5","lr=2e-5")
s=s.replace("history=[];best=float('inf');stale=0;selected=False", "history=[];best=float('inf');stale=0;selected=False\n    # Preserve parent predictions on OLD TRAINING RGB only, never validation.\n    teacher=ObjectVerifier(mode='rgb_only').cuda();teacher.load_state_dict(saved['verifier']);teacher.eval();teacher_probs=[]\n    with torch.inference_mode():\n        for at in range(0,len(old['training']['rgb']),256):\n            rgb=torch.tensor(old['training']['rgb'][at:at+256],device='cuda').float();meta=torch.tensor(old['training']['meta'][at:at+256],device='cuda').float();teacher_probs.append(teacher(rgb.new_zeros((len(rgb),1)),meta,rgb)['identity'].softmax(-1).cpu().numpy())\n    teacher_probs=np.concatenate(teacher_probs);del teacher;torch.cuda.empty_cache();old_count=len(teacher_probs)")
s=s.replace("assert torch.isfinite(loss);optimizer.zero_grad", "old_mask=ix<old_count\n            if old_mask.any():\n                soft=torch.tensor(teacher_probs[ix[old_mask]],device='cuda');loss=loss+F.kl_div(pred['identity'][old_mask].log_softmax(-1),soft,reduction='batchmean')\n            assert torch.isfinite(loss);optimizer.zero_grad")
s=s.replace("and (false(baseline['new_close'])==0", "and metrics['new_close']['selected_operating_point']['target_recall']>=baseline['new_close']['selected_operating_point']['target_recall']-.02 and (false(baseline['new_close'])==0")
s=s.replace("validation=metrics['new_close']", "validation=metrics['wide_rehearsal']")
s=s.replace("maximum_epochs=8,patience=3,selection=", "maximum_epochs=8,patience=3,old_training_only_KL_rehearsal_weight=1.0,learning_rate=2e-5,runtime_review_point_source='wide_rehearsal unchanged known-design distribution; new close subset separately reported, original80gatefalse',selection=")
s=s.replace("'selected_validation']=torch.load(OUT/'best.pt',map_location='cpu',weights_only=False)['validation']", "'selected_validation']=torch.load(OUT/'best.pt',map_location='cpu',weights_only=False)['validation']")
compile(s,'train_static_verifier_v47.py','exec');(R/'train_static_verifier_v47.py').write_text(s)
s=(R/'launch_training_v45.py').read_text().replace('static_training_v45','static_training_v47').replace('train_static_verifier_v45','train_static_verifier_v47')
# Preserve original genuine agent review receipt rather than rewrite it.
a=s.index('review=dict(');b=s.index('with(R/',a);s=s[:a]+"assert json.loads((D/'agent_visual_review.json').read_text())['passed']\n"+s[b:]
(R/'launch_training_v47.py').write_text(s)
