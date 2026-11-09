import torch
from visual_loss_v59 import correct_teacher_kl,identity_loss
x=torch.tensor([[.2,.4,-.5],[.3,-.2,.8]],requires_grad=True);labels=torch.tensor([2,2]);a=torch.tensor([[.02,.96,.02],[.1,.1,.8]]);b=torch.tensor([[.1,.8,.1],[.1,.1,.8]])
l=correct_teacher_kl(x,a,labels);ga=torch.autograd.grad(l,x,retain_graph=True)[0];lb=correct_teacher_kl(x,b,labels);gb=torch.autograd.grad(lb,x,retain_graph=True)[0];assert torch.equal(ga,gb)and torch.all(ga[0]==0)and torch.any(ga[1]!=0)
invalid=identity_loss(x,torch.tensor([-100,-100]),torch.ones(3),a);assert invalid==0;assert torch.all(torch.autograd.grad(invalid,x)[0]==0)
y=identity_loss(x,labels,torch.ones(3),a);assert torch.isfinite(y)
print('PASSED: wrong teacher has zero KL gradient, correct teacher retains gradient, invalid labels zero, hard-negative CE finite')
