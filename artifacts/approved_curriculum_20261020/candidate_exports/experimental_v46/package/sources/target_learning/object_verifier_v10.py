"""Factor boat-design identity and landing-marker visibility explicitly."""
import torch
from torch import nn
from .object_verifier import ObjectVerifier as Previous,regions


class ObjectVerifier(Previous):
    def __init__(self):
        super().__init__();self.marker=nn.Linear(64,1);nn.init.constant_(self.marker.bias,-1.)

    def forward(self,features,metadata):
        value=torch.cat([self.image(features),metadata],1)
        hidden=self.classifier[:-1](value)
        return dict(identity=self.classifier[-1](hidden),marker=self.marker(hidden)[:,0])


def verify(model,fine,context,frames):
    boxes=[];indices=[];references=[]
    for b,frame in enumerate(frames):
        for p in frame:boxes.append([*p['pixel'],*p['size_px']]);indices.append(b);references.append(p)
    if not boxes:return frames
    features,meta=regions(fine,context,boxes,indices);output=model(features,meta)
    probs=output['identity'].softmax(-1).detach().cpu().tolist();markers=output['marker'].sigmoid().detach().cpu().tolist()
    for p,prob,marker in zip(references,probs,markers):
        p['original_detection_channel_is_boat']=p['boat'];p['boat']=True
        p['previous_dense_target_probability']=p['target_probability'];p['previous_dense_pad_visibility']=p['pad_visibility_probability']
        p['target_probability']=prob[1];p['wrong_object_probability']=prob[0];p['unknown_probability']=prob[2]
        p['identity_support_probability']=prob[0]+prob[1]
        p['marker_probability']=marker;p['pad_visibility_probability']=marker
    return frames
