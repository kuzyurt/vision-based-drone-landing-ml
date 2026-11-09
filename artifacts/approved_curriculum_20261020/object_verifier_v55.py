"""Conservative two-model agreement; never adds target/wrong-design confidence."""
import torch
from torch import nn
from .object_verifier_v12 import ObjectVerifier as Single,verify,rgb_regions

def agreement(first,second):
 a=first['identity'].softmax(-1);b=second['identity'].softmax(-1);target=torch.minimum(a[:,1],b[:,1]);wrong=torch.minimum(a[:,0],b[:,0]);unknown=(1-target-wrong).clamp_min(0);prob=torch.stack((wrong,target,unknown),-1)
 marker=torch.minimum(first['marker'].sigmoid(),second['marker'].sigmoid()).clamp(1e-7,1-1e-7)
 return dict(identity=prob.clamp_min(1e-20).log(),marker=torch.logit(marker))
class ObjectVerifier(nn.Module):
 def __init__(self,mode='rgb_intersection_v55'):
  super().__init__();assert mode=='rgb_intersection_v55';self.mode=mode;self.members=nn.ModuleList([Single(mode='rgb_only'),Single(mode='rgb_only')])
 def forward(self,features,metadata,rgb):return agreement(self.members[0](features,metadata,rgb),self.members[1](features,metadata,rgb))
