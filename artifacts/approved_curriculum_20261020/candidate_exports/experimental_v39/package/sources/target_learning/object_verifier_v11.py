"""Add direct RGB detail to unchanged design/marker task semantics."""
import torch
from torch import nn
from torch.nn import functional as F
from .object_verifier_v10 import ObjectVerifier as Previous
from .object_verifier import regions


def rgb_regions(rgb,metadata):
    # Input RGB [N,3,360,640], candidate metadata from deployed detections only.
    if rgb.dtype==torch.uint8:rgb=rgb.float()/255.
    axis=(torch.arange(96,device=rgb.device,dtype=rgb.dtype)+.5)/96-.5
    yy,xx=torch.meshgrid(axis,axis,indexing='ij');unit=torch.stack((xx,yy),-1)
    center=metadata[:,:2]*rgb.new_tensor([640.,360.]);size=metadata[:,2:4]*rgb.new_tensor([640.,360.])
    pixels=center[:,None,None,:]+1.5*size[:,None,None,:]*unit[None]
    grid=pixels/rgb.new_tensor([640.,360.])*2-1
    if len(rgb)==1:rgb=rgb.expand(len(metadata),-1,-1,-1)
    return F.grid_sample(rgb,grid,align_corners=False,padding_mode='zeros').half()


class ObjectVerifier(Previous):
    def __init__(self):
        super().__init__();layers=[];channels=3
        for width in [16,32,64,64]:
            layers.extend([nn.Conv2d(channels,width,3,stride=2,padding=1),nn.GroupNorm(4,width),nn.SiLU()]);channels=width
        self.rgb=nn.Sequential(*layers,nn.AdaptiveAvgPool2d((3,3)),nn.Flatten(),nn.Linear(64*3*3,128),nn.SiLU(),nn.Linear(128,64),nn.SiLU())
        self.rgb_identity=nn.Linear(64,3);self.rgb_marker=nn.Linear(64,1)
        nn.init.zeros_(self.rgb_identity.weight);nn.init.zeros_(self.rgb_identity.bias)
        nn.init.zeros_(self.rgb_marker.weight);nn.init.zeros_(self.rgb_marker.bias)

    def forward(self,features,metadata,rgb):
        old=super().forward(features,metadata);detail=self.rgb(rgb.float())
        return dict(identity=old['identity']+self.rgb_identity(detail),marker=old['marker']+self.rgb_marker(detail)[:,0])


def verify(model,fine,context,frames,rgb):
    boxes=[];indices=[];references=[]
    for b,frame in enumerate(frames):
        for p in frame:boxes.append([*p['pixel'],*p['size_px']]);indices.append(b);references.append(p)
    if not boxes:return frames
    features,meta=regions(fine,context,boxes,indices)
    image=torch.as_tensor(rgb,device=fine.device).permute(2,0,1)[None]
    cropped=rgb_regions(image,meta);output=model(features,meta,cropped)
    probs=output['identity'].softmax(-1).detach().cpu().tolist();markers=output['marker'].sigmoid().detach().cpu().tolist()
    for p,prob,marker in zip(references,probs,markers):
        p['original_detection_channel_is_boat']=p['boat'];p['boat']=True
        p['previous_dense_target_probability']=p['target_probability'];p['previous_dense_pad_visibility']=p['pad_visibility_probability']
        p['target_probability']=prob[1];p['wrong_object_probability']=prob[0];p['unknown_probability']=prob[2]
        p['identity_support_probability']=prob[0]+prob[1];p['marker_probability']=marker;p['pad_visibility_probability']=marker
    return frames
