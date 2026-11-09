from pathlib import Path
R=Path(__file__).parent;s=(R/'train_static_verifier_v53b.py').read_text().replace("OUT=ROOT/'perception_training_v53'","OUT=ROOT/'perception_training_v59'")
s=s.replace('from torch.nn import functional as F','from torch.nn import functional as F\nfrom visual_loss_v59 import correct_teacher_kl,identity_loss')
s=s.replace("range(0,len(old['training']['rgb']),256)","range(0,len(train['rgb']),256)").replace("old['training']['rgb'][at:at+256]","train['rgb'][at:at+256]").replace("old['training']['meta'][at:at+256]","train['meta'][at:at+256]")
s=s.replace("old_count=len(teacher_probs)","old_count=len(old['training']['classes'])\n    good=(train['classes'][:old_count]>=0)&(teacher_probs[:old_count].argmax(-1)==train['classes'][:old_count]);hard=(teacher_probs[:,1]>=.9)&(train['classes']>=0)&(train['classes']!=1)\n    save(OUT/'training_teacher_correction_receipt.json',dict(old_training_regions=old_count,correct_teacher_KL_regions=int(good.sum()),incorrect_or_invalid_teacher_KL_excluded=int(old_count-good.sum()),parent_high_confidence_false_target_training_regions=int(hard.sum()),false_target_weight=3,validation_or_failed_raw_used_for_mining=False))")
a="(F.cross_entropy(pred['identity'],y,weight=weights,ignore_index=-100)if(y>=0).any()else pred['identity'].sum()*0)"
b="identity_loss(pred['identity'],y,weights,torch.tensor(teacher_probs[ix],device='cuda'))"
assert a in s;s=s.replace(a,b)
s=s.replace("F.kl_div(pred['identity'][old_mask].log_softmax(-1),soft,reduction='batchmean')","correct_teacher_kl(pred['identity'][old_mask],soft,y[old_mask])")
s=s.replace("old_training_only_KL_rehearsal_weight=1.0", "old_training_only_KL_rehearsal_weight=1.0,distill_only_GT_correct_parent_predictions=True,training_only_false_target_mining_weight=3,loss_source_sha256=sha(ROOT/'visual_loss_v59.py')")
compile(s,'train_static_verifier_v59.py','exec');(R/'train_static_verifier_v59.py').write_text(s)
s=(R/'launch_training_v53b.py').read_text().replace('static_training_v53','static_training_v59').replace('train_static_verifier_v53b','train_static_verifier_v59');compile(s,'launch_training_v59.py','exec');(R/'launch_training_v59.py').write_text(s)
