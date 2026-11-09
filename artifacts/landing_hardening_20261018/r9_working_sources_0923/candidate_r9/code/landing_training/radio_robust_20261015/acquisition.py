import torch
from torch import nn
class AcquisitionHead(nn.Module):
    def __init__(self):
        super().__init__();self.register_buffer('mean',torch.zeros(1728));self.register_buffer('std',torch.ones(1728))
        self.network=nn.Sequential(nn.Linear(1728,256),nn.ReLU(),nn.Dropout(.1),nn.Linear(256,128),nn.ReLU(),nn.Linear(128,3))
    def forward(self,x):return self.network(((x-self.mean)/self.std).clamp(-12,12))
