"""Whole-proposal appearance verification using existing frozen image features.

No task truth, range or segmentation inputs. Metadata describes the predicted
image box only. Native prototype; browser operator/parity checks remain required.
"""
import torch
from torch import nn
from torch.nn import functional as F


def regions(fine,context,boxes,batch_indices,*,expansion=1.5):
    """Sample a full candidate and its context, preserving real frame edges."""
    device=fine.device;boxes=torch.as_tensor(boxes,device=device,dtype=fine.dtype)
    batch_indices=torch.as_tensor(batch_indices,device=device,dtype=torch.long)
    if len(boxes)==0:return fine.new_empty((0,72,8,8)),fine.new_empty((0,8))
    center=boxes[:,:2];size=boxes[:,2:].clamp_min(1.)
    axis=(torch.arange(8,device=device,dtype=fine.dtype)+.5)/8-.5
    yy,xx=torch.meshgrid(axis,axis,indexing='ij');unit=torch.stack((xx,yy),-1)
    pixels=center[:,None,None,:]+unit[None]*size[:,None,None,:]*expansion
    grid=pixels/fine.new_tensor([640.,360.])*2-1
    values=torch.cat([F.grid_sample(fine[batch_indices],grid,align_corners=False,padding_mode='zeros'),
                      F.grid_sample(context[batch_indices],grid,align_corners=False,padding_mode='zeros')],1)
    lo=center-size/2;hi=center+size/2
    edge=torch.stack([lo[:,0]<3,lo[:,1]<3,hi[:,0]>637,hi[:,1]>357],1).to(fine.dtype)
    meta=torch.cat([center/fine.new_tensor([640.,360.]),size/fine.new_tensor([640.,360.]),edge],1)
    return values,meta


class ObjectVerifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.image=nn.Sequential(nn.Conv2d(72,32,1),nn.GroupNorm(8,32),nn.SiLU(),
            nn.Conv2d(32,32,3,padding=1),nn.GroupNorm(8,32),nn.SiLU(),nn.Flatten())
        self.classifier=nn.Sequential(nn.Linear(32*8*8+8,192),nn.SiLU(),nn.Dropout(.1),
            nn.Linear(192,64),nn.SiLU(),nn.Linear(64,3))

    def forward(self,regions,metadata):
        return self.classifier(torch.cat([self.image(regions),metadata],1))


def verify(model,fine,context,frames):
    boxes=[];indices=[];references=[]
    for b,frame in enumerate(frames):
        for p in frame:
            boxes.append([*p['pixel'],*p['size_px']]);indices.append(b);references.append(p)
    if not boxes:return frames
    features,meta=regions(fine,context,boxes,indices)
    probability=model(features,meta).softmax(-1).detach().cpu().tolist()
    for p,prob in zip(references,probability):
        # Both dense channels supplied proposals during verifier validation.
        # They are potential objects here; the verifier decides identity.
        p['original_detection_channel_is_boat']=p['boat'];p['boat']=True
        p['previous_dense_target_probability']=p['target_probability']
        p['previous_dense_support_probability']=p.get('identity_support_probability')
        p['target_probability']=prob[1]
        p['wrong_object_probability']=prob[0]
        p['identity_support_probability']=prob[0]+prob[1]
        p['unknown_probability']=prob[2]
    return frames
