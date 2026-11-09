"""Recognition with separately supervised visual identity support.

Target confidence is conditional on enough visible identifying context. A cold
crop of a shared marker does not establish boat identity; tracking handles it.
"""
import torch
from torch import nn
from .discriminator import Discriminator as Previous, decode as previous_decode
from .object_nms import suppress


class Discriminator(Previous):
    def __init__(self):
        super().__init__()
        self.support=nn.Conv2d(48,1,1)
        nn.init.constant_(self.support.bias,-2.)

    def forward(self,fine,context):
        from torch.nn import functional as F
        x=torch.cat((self.fine(fine),F.interpolate(self.context(context),size=fine.shape[-2:],mode='bilinear',align_corners=False)),1)
        x=self.merge(x)
        return dict(heat=self.heat(x),offset=.5*self.offset(x).tanh(),size=self.size(x).clamp(-6,2),
            identity=self.identity(x),pad=self.pad(x).tanh(),pad_visible=self.pad_visible(x),support=self.support(x))


def decode(output,*,minimum_presence=.2,topk=32,nms_iou=.3):
    rows=previous_decode(output,minimum_presence=minimum_presence,topk=topk)
    _,_,h,w=output['support'].shape
    for b,frame in enumerate(rows):
        for p in frame:
            # Previous decoder includes subcell offsets; recover its nearest
            # grid cell, whose offset is constrained to half a feature cell.
            x=min(w-1,max(0,int(p['pixel'][0]/(640/w))))
            y=min(h-1,max(0,int(p['pixel'][1]/(360/h))))
            p['identity_support_probability']=float(output['support'][b,0,y,x].sigmoid())
        rows[b]=suppress(frame,nms_iou)
    return rows
