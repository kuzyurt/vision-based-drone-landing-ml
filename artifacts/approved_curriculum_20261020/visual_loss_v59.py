"""Training-only hard negatives and correct-teacher rehearsal; no task actions."""
import torch
from torch.nn import functional as F

def correct_teacher_kl(logits,teacher,labels):
 good=(labels>=0)&(teacher.argmax(-1)==labels)
 return F.kl_div(logits[good].log_softmax(-1),teacher[good],reduction='batchmean')if good.any()else logits.sum()*0

def identity_loss(logits,labels,class_weights,parent_probability):
 valid=labels>=0
 if not valid.any():return logits.sum()*0
 hard=((parent_probability[:,1]>=.9)&(labels!=1)&valid).to(logits.dtype)*2+1
 per=F.cross_entropy(logits,labels,weight=class_weights,ignore_index=-100,reduction='none')
 return (per*hard).sum()/(class_weights[labels[valid]]*hard[valid]).sum().clamp_min(1e-8)
