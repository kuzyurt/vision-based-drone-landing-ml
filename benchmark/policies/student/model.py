"""Frozen R15 vision features and an initialized multi-boat acquisition head."""
from __future__ import annotations
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from common import config, r15_module, weight_path

EVIDENCE = ('unknown_boat','target_or_similar','different_boat','target_boat')


def load_backbone(device='cpu'):
    cls = r15_module('radio_robust_20261015.model').RadioRobustPoseModel
    saved = torch.load(weight_path('pose'),map_location='cpu',weights_only=False)
    model=cls();model.load_state_dict(saved['model'],strict=True)
    for p in model.parameters():p.requires_grad=False
    return model.to(device).eval()


@torch.no_grad()
def encode_maps(base, images):
    backbone=base.backbone
    x=(images.float()/255.-backbone.image_mean)/backbone.image_std
    fine=None
    for index, layer in enumerate(backbone.encoder):
        x=layer(x)
        if index==3:fine=x
        if index==8:return fine,x
    raise AssertionError('R15 encoder changed')


class SearchHead(nn.Module):
    def __init__(self, initialize=True):
        super().__init__()
        spatial=r15_module('radio_robust_20261015.spatial_acquisition').SpatialAcquisition
        self.spatial=spatial()
        if initialize:
            saved=torch.load(weight_path('spatial'),map_location='cpu',weights_only=False)
            self.spatial.load_state_dict(saved['model'],strict=True)
        self.evidence=nn.Conv2d(48,4,1)
        self.identity=nn.Conv2d(48,2,1)

    def forward(self, fine, context):
        s=self.spatial
        joined=torch.cat((s.fine(fine),F.interpolate(s.context(context),size=fine.shape[-2:],mode='bilinear',align_corners=False)),1)
        feature=s.merge(joined)
        return dict(heat=s.heat(feature)[:,0],offset=.5*torch.tanh(s.offset(feature)),
            presence=s.presence(feature.amax((-2,-1)))[:,0],
            evidence=self.evidence(feature),identity=self.identity(feature))


def targets(boats, height=45, width=80):
    heat=np.zeros((height,width),np.float32)
    ignore=np.zeros((height,width),bool)
    offsets=np.zeros((2,height,width),np.float32)
    positive=np.zeros((height,width),bool)
    evidence=np.full((height,width),-100,np.int64)
    identity=np.full((height,width),-100,np.int64)
    yy,xx=np.mgrid[:height,:width]
    occupied=set();conflicts=set()
    for boat in boats:
        x0,y0,x1,y1=boat['bbox']
        if not boat['boat_detection_valid']:
            xa=max(0,int(x0*width/640));xb=min(width,int(x1*width/640)+1)
            ya=max(0,int(y0*height/360));yb=min(height,int(y1*height/360)+1)
            ignore[ya:yb,xa:xb]=True
            continue
        cx=(x0+x1)*.5/640*width-.5;cy=(y0+y1)*.5/360*height-.5
        col=int(np.clip(round(cx),0,width-1));row=int(np.clip(round(cy),0,height-1))
        heat=np.maximum(heat,np.exp(-((xx-col)**2+(yy-row)**2)/(2*1.5**2)).astype(np.float32))
        key=(row,col)
        if key in occupied:conflicts.add(key)
        occupied.add(key)
        positive[row,col]=True;offsets[:,row,col]=[np.clip(cx-col,-.5,.5),np.clip(cy-row,-.5,.5)]
        evidence[row,col]=EVIDENCE.index(boat['evidence'])
        if boat['identity_supervision_valid']:
            identity[row,col]=int(boat['evidence']=='target_boat')
    for row,col in conflicts:
        evidence[row,col]=identity[row,col]=-100;positive[row,col]=False
    # Real detections win over ignore regions of tiny overlapping fragments.
    ignore[heat==1]=False
    return {k:torch.from_numpy(v) for k,v in dict(heat=heat,ignore=ignore,offset=offsets,
        positive=positive,evidence=evidence,identity=identity).items()}


def macro_ce(logits, labels):
    present=labels!=-100
    if not present.any():return logits.sum()*0.
    losses=F.cross_entropy(logits,labels,ignore_index=-100,reduction='none')
    return torch.stack([losses[labels==i].mean() for i in labels[present].unique()]).mean()


def loss(output, target):
    heat=target['heat'];valid=~target['ignore']
    p=output['heat'].sigmoid().clamp(1e-5,1-1e-5)
    pos=heat==1;neg=(heat<1)&valid
    positive_loss=-(p.log()*(1-p).square()*pos).sum()
    negative_loss=-((1-p).log()*p.square()*(1-heat).pow(4)*neg).sum()
    focal=(positive_loss+negative_loss)/pos.sum().clamp_min(1)
    mask=target['positive']
    offset=F.smooth_l1_loss(output['offset'].permute(0,2,3,1)[mask],
                          target['offset'].permute(0,2,3,1)[mask]) if mask.any() else output['offset'].sum()*0.
    presence=F.binary_cross_entropy_with_logits(output['presence'],pos.flatten(1).any(1).float())
    evidence=macro_ce(output['evidence'],target['evidence'])
    identity=macro_ce(output['identity'],target['identity'])
    values=dict(heat=focal,offset=offset,presence=presence,evidence=evidence,identity=identity)
    return focal+offset+.1*presence+evidence+identity,values


@torch.inference_mode()
def decode(output, threshold=None):
    c=config();threshold=min(float(c['proposal_threshold']),0.36) if threshold is None else threshold
    heat=output['heat'].sigmoid()
    maxima=(heat==F.max_pool2d(heat[:,None],5,1,2)[:,0])&(heat>=threshold)
    proposals=[]
    for batch in range(len(heat)):
        scores=(heat[batch]*maxima[batch]).flatten()
        values,indices=scores.topk(min(c['max_objects']*2,scores.numel()))
        items=[];height,width=heat.shape[-2:]
        for confidence,index in zip(values,indices):
            if float(confidence)<threshold:continue
            row=int(index)//width;col=int(index)%width
            offset=output['offset'][batch,:,row,col]
            px=float((col+.5+offset[0])*640/width)
            py=float((row+.5+offset[1])*360/height)
            if any((px-it['pixel'][0])**2+(py-it['pixel'][1])**2<28.**2 for it in items):
                continue
            ev=output['evidence'][batch,:,row,col].softmax(0)
            ident=output['identity'][batch,:,row,col].softmax(0)
            k=int(ev.argmax());evidence=EVIDENCE[k]
            target_like=float(ev[1]+ev[3])
            if float(ev[k])<c['evidence_threshold']:
                if target_like>=0.60:
                    evidence='target_boat' if (float(ev[3])>=0.42 and float(ident[1])>=0.82) else 'target_or_similar'
                else:
                    evidence='unknown_boat'
            if evidence=='target_boat' and float(ident[1])<min(float(c['identity_threshold']),0.85):
                evidence='target_or_similar'
            if evidence=='different_boat' and float(ident[0])<c['identity_threshold']:
                evidence='unknown_boat'
            items.append(dict(pixel=[px,py],
                confidence=float(confidence),evidence=evidence,
                identity_target_probability=float(ident[1])))
            if len(items)>=c['max_objects']:
                break
        proposals.append(items)
    return proposals
