"""Independent frozen visual recurrence with a trainable, bounded radio fusion head."""
import torch
from torch import nn
from .parent_model import RadioRobustPoseModel as ParentModel

class RadioRobustPoseModel(ParentModel):
    MAX_RADIO_WEIGHT=.35
    def __init__(self,source=None):
        super().__init__(source)
        self.fusion_gate=nn.Sequential(nn.Linear(13,48),nn.SiLU(),nn.Linear(48,2))
        nn.init.zeros_(self.fusion_gate[-1].weight)
        nn.init.constant_(self.fusion_gate[-1].bias,-2.)

    def visual_features(self,features,numeric,hidden=None):
        # Match the preserved parent's explicit missing-radio path exactly.
        # No radio value, validity, quality, age or dock status enters recurrence.
        visual=numeric.clone();visual[...,11:17]=0.;visual[...,19]=3.1;visual[...,21]=0.
        visual[...,22]=self.backbone.observation_mean[22]
        quality=numeric.new_tensor([100.,10.]).expand(*numeric.shape[:-1],2)
        return super().forward_features(features,visual,hidden,quality)

    def fusion_inputs(self,visual,numeric,uncertainty):
        available=(numeric[...,21]>.5)&(numeric[...,19]<3.)
        available &= torch.isfinite(numeric[...,11:17]).all(-1)&torch.isfinite(uncertainty).all(-1)
        age=numeric[...,19].clamp(0.,3.)
        radio=torch.nan_to_num(numeric[...,11:17])
        # Held boat coordinates are relative to the drone NOW, while boat
        # velocity is absolute in that heading frame. Extrapolate boat motion.
        position=radio[...,:3]+radio[...,3:6]*age[...,None]
        velocity=radio[...,3:6]-numeric[...,:3]
        dp=position-visual[...,1:4];dv=velocity-visual[...,4:7]
        values=torch.cat((dp/5.,dv,torch.log1p(uncertainty.clamp(0.,1000.)),
            age[...,None]/3.,visual[...,:1].sigmoid(),dp.norm(dim=-1,keepdim=True)/5.,
            dv.norm(dim=-1,keepdim=True),torch.log1p(visual[...,1:4].norm(dim=-1,keepdim=True))/4.),-1)
        return values,position,velocity,available

    def fuse(self,visual,numeric,uncertainty):
        features,position,velocity,available=self.fusion_inputs(visual,numeric,uncertainty)
        logits=self.fusion_gate(features)
        weights=logits.sigmoid()*self.MAX_RADIO_WEIGHT*available[...,None]
        prediction=visual.clone()
        prediction[...,1:4]=visual[...,1:4]+weights[...,0:1]*(position-visual[...,1:4])
        prediction[...,4:7]=visual[...,4:7]+weights[...,1:2]*(velocity-visual[...,4:7])
        return prediction,weights,logits,position,velocity

    def forward_features(self,features,numeric,hidden=None,uncertainty=None):
        if uncertainty is None:uncertainty=numeric.new_tensor([.25,.1]).expand(*numeric.shape[:-1],2)
        visual,visual_pose,hidden=self.visual_features(features,numeric,hidden)
        prediction,weights,_,_,_=self.fuse(visual,numeric,uncertainty)
        self.last_fusion_weights=weights.detach()
        self.last_independent_visual_prediction=visual.detach()
        return prediction,visual_pose,hidden
