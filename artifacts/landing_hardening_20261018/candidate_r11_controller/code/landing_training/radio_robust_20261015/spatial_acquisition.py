"""Image-only point heatmap retaining spatial features before global compression."""
import torch
from torch import nn
from torch.nn import functional as F


class SpatialAcquisition(nn.Module):
    def __init__(self):
        super().__init__()
        self.fine=nn.Sequential(nn.Conv2d(24,24,1),nn.GroupNorm(6,24),nn.SiLU())
        self.context=nn.Sequential(nn.Conv2d(48,24,1),nn.GroupNorm(6,24),nn.SiLU())
        self.merge=nn.Sequential(nn.Conv2d(48,48,3,padding=1),nn.GroupNorm(8,48),nn.SiLU(),
            nn.Conv2d(48,48,3,padding=1),nn.GroupNorm(8,48),nn.SiLU())
        self.heat=nn.Conv2d(48,1,1);self.offset=nn.Conv2d(48,2,1)
        self.presence=nn.Sequential(nn.Linear(48,32),nn.SiLU(),nn.Linear(32,1))
    def forward(self,fine,context):
        joined=torch.cat((self.fine(fine),F.interpolate(self.context(context),size=fine.shape[-2:],mode='bilinear',align_corners=False)),1)
        feature=self.merge(joined)
        return self.heat(feature)[:,0],.5*torch.tanh(self.offset(feature)),self.presence(feature.amax((-2,-1)))[:,0]


def encode_spatial(backbone,images):
    x=images.float()/255.;x=(x-backbone.image_mean)/backbone.image_std
    fine=None
    for index,layer in enumerate(backbone.encoder):
        x=layer(x)
        if index==3:fine=x
        if index==8:return fine,x
    raise AssertionError('Unexpected encoder layout')


def decode_spatial(output):
    heat,offset,presence=output;batch,height,width=heat.shape
    index=heat.flatten(1).argmax(1);row=index//width;col=index%width
    local=offset.flatten(2)[torch.arange(batch,device=heat.device),:,index]
    pixel=torch.stack(((col+.5+local[:,0])*640/width,(row+.5+local[:,1])*360/height),1)
    return presence,pixel
