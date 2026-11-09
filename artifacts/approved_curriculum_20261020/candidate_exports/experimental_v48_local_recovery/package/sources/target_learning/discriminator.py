"""Multi-instance boat candidates with independent target identity and pad heads."""
import torch
from torch import nn
from torch.nn import functional as F


class Discriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.fine=nn.Sequential(nn.Conv2d(24,24,1),nn.GroupNorm(6,24),nn.SiLU())
        self.context=nn.Sequential(nn.Conv2d(48,24,1),nn.GroupNorm(6,24),nn.SiLU())
        self.merge=nn.Sequential(nn.Conv2d(48,48,3,padding=1),nn.GroupNorm(8,48),nn.SiLU(),
                                 nn.Conv2d(48,48,3,padding=1),nn.GroupNorm(8,48),nn.SiLU())
        self.heat=nn.Conv2d(48,2,1)  # boat-like candidate / other distractor
        self.offset=nn.Conv2d(48,2,1)
        self.size=nn.Conv2d(48,2,1)
        self.identity=nn.Conv2d(48,1,1)
        self.pad=nn.Conv2d(48,2,1)
        self.pad_visible=nn.Conv2d(48,1,1)
        nn.init.constant_(self.heat.bias,-2.2)

    def initialize_shared(self,old_spatial):
        for name in ['fine','context','merge','offset']:
            getattr(self,name).load_state_dict(getattr(old_spatial,name).state_dict())

    def forward(self,fine,context):
        x=torch.cat((self.fine(fine),F.interpolate(self.context(context),size=fine.shape[-2:],mode='bilinear',align_corners=False)),1)
        x=self.merge(x)
        return dict(heat=self.heat(x),offset=.5*self.offset(x).tanh(),size=self.size(x).clamp(-6,2),
                    identity=self.identity(x),pad=self.pad(x).tanh(),pad_visible=self.pad_visible(x))


def decode(output,*,minimum_presence=.2,topk=12):
    """Multiple peaks; probabilities require separate validation calibration."""
    heat=output['heat'].sigmoid();maximum=F.max_pool2d(heat,3,1,1)
    peaks=heat*(heat==maximum);batch,_,h,w=heat.shape
    values,indices=peaks.flatten(1).topk(topk,dim=1)
    result=[]
    for b in range(batch):
        rows=[]
        for value,index in zip(values[b],indices[b]):
            if float(value)<minimum_presence:continue
            channel=int(index)//(h*w);cell=int(index)%(h*w);y,x=divmod(cell,w)
            offset=output['offset'][b,:,y,x]
            center=torch.stack((x+.5+offset[0],y+.5+offset[1]))*offset.new_tensor([640/w,360/h])
            size=output['size'][b,:,y,x].exp()*offset.new_tensor([640.,360.])
            identity=float(output['identity'][b,0,y,x].sigmoid())
            pad_visible=float(output['pad_visible'][b,0,y,x].sigmoid())
            pad=center+output['pad'][b,:,y,x]*size
            rows.append(dict(pixel=center.tolist(),size_px=size.tolist(),boat=channel==0,
                presence=float(value),target_probability=identity,pad_visibility_probability=pad_visible,
                pad_pixel=pad.tolist()))
        result.append(rows)
    return result
