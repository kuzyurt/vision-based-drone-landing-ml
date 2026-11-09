"""Compact spatial vision, telemetry and causal recurrent action prediction."""
import math
import numpy as np
import torch
from torch import nn
from torchvision.models import mobilenet_v3_small,MobileNet_V3_Small_Weights
from .recording import numeric_observation

ACTION_SCALE=torch.tensor([2.,2.,.7,.5,math.radians(50),math.radians(40)])

class LandingPolicy(nn.Module):
    def __init__(self,pretrained=False,freeze_encoder=False):
        super().__init__()
        backbone=mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT if pretrained else None)
        self.encoder=backbone.features
        if freeze_encoder:
            for parameter in self.encoder.parameters():parameter.requires_grad=False
        self.visual=nn.Sequential(nn.Linear(576*3,256),nn.ReLU())
        self.telemetry=nn.Sequential(nn.Linear(32,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU())
        self.gru=nn.GRU(320,128,batch_first=True)
        self.actions=nn.Linear(128,6);self.auxiliary=nn.Linear(128,10)
        self.register_buffer('observation_mean',torch.zeros(32));self.register_buffer('observation_std',torch.ones(32))
        self.register_buffer('image_mean',torch.tensor([.485,.456,.406]).view(1,3,1,1));self.register_buffer('image_std',torch.tensor([.229,.224,.225]).view(1,3,1,1))

    def forward(self,images,telemetry,hidden=None):
        return self.forward_features(self.encode_images(images),telemetry,hidden)

    def encode_images(self,images):
        """Fixed spatial features can be cached while the encoder is frozen."""
        batch,steps=images.shape[:2]
        image=images.reshape(-1,*images.shape[2:]).float()/255.
        features=self.encoder((image-self.image_mean)/self.image_std)
        n,channels,height,width=features.shape
        probability=torch.softmax(features.reshape(n,channels,-1),dim=-1)
        yy,xx=torch.meshgrid(torch.linspace(-1,1,height,device=images.device),torch.linspace(-1,1,width,device=images.device),indexing='ij')
        spatial=torch.stack(((probability*xx.flatten()).sum(-1),(probability*yy.flatten()).sum(-1),features.mean((2,3))),dim=-1).reshape(n,-1)
        return spatial.reshape(batch,steps,-1)

    def forward_features(self,spatial,telemetry,hidden=None):
        visual=self.visual(spatial)
        state=self.telemetry((telemetry-self.observation_mean)/self.observation_std)
        recurrent,hidden=self.gru(torch.cat((visual,state),dim=-1),hidden)
        return torch.tanh(self.actions(recurrent)),self.auxiliary(recurrent),hidden

def normalize_actions(actions):
    scale=ACTION_SCALE.to(actions.device).expand_as(actions).clone()
    scale[...,2]=torch.where(actions[...,2]<0,1.,.7)
    return actions/scale

def denormalize_action(action):
    a=np.asarray(action,dtype=float)*ACTION_SCALE.cpu().numpy()
    if a[2]<0:a[2]/=.7
    norm=np.linalg.norm(a[:2])
    if norm>2:a[:2]*=2/norm
    return a

class PolicyRuntime:
    def __init__(self,checkpoint,device='cpu'):
        self.device=torch.device(device);self.model=LandingPolicy().to(self.device)
        checkpoint=torch.load(checkpoint,map_location=self.device,weights_only=False)
        if checkpoint.get('schema')!='aerodock.landing.checkpoint.v1':raise ValueError('Unknown checkpoint schema')
        self.metadata={key:checkpoint.get(key) for key in ('schema','epoch','dataset_sha256','review_manifest_sha256','training')}
        self.model.load_state_dict(checkpoint['model']);self.model.eval();self.hidden=None
    def reset(self):self.hidden=None
    @torch.inference_mode()
    def act(self,rgb,observation):
        image=torch.from_numpy(rgb.copy()).permute(2,0,1)[None,None].to(self.device)
        telemetry=torch.from_numpy(numeric_observation({'observation':observation}))[None,None].to(self.device)
        action,aux,self.hidden=self.model(image,telemetry,self.hidden)
        return denormalize_action(action[0,0].cpu().numpy()),{'pad_visibility_probability':float(torch.sigmoid(aux[0,0,0]).cpu()),'stable_contact_probability':float(torch.sigmoid(aux[0,0,9]).cpu())}
