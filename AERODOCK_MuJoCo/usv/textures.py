"""Small seamless, procedural material tiles. No downloads or stretched photos."""
from pathlib import Path
import numpy as np
from PIL import Image


def water_pixels(t=0.,size=256,roughness=.12):
    y,x=np.mgrid[0:size,0:size].astype(float)/size
    sx=np.zeros_like(x); sy=np.zeros_like(y)
    for a,kx,ky,speed,phase in ((.6,3,1,.7,0),(.4,-2,5,1.1,1.7),(.25,9,-3,1.6,2.3),(.18,13,11,2.1,.4),(.1,-19,7,2.7,1.8)):
        q=2*np.pi*(kx*x+ky*y)-speed*t+phase
        sx+=a*kx*np.sin(q); sy+=a*ky*np.sin(q)
    scale=.016+roughness*.08
    nx=sx*scale; ny=sy*scale
    nz=np.ones_like(x)
    length=np.sqrt(nx*nx+ny*ny+nz*nz)
    diffuse=np.clip((-.35*nx-.25*ny+nz*.9)/length,0,1)
    glint=np.power(np.clip((-.14*nx+.09*ny+nz*.98)/length,0,1),85)
    fresnel=np.clip(.12+.12*(nx*nx+ny*ny),.12,.65)
    base=np.stack([32+32*diffuse,69+40*diffuse,86+45*diffuse],axis=-1)
    base+=glint[...,None]*np.array([63,68,69])
    base+=fresnel[...,None]*np.array([23,29,33])
    return np.clip(base,0,255).astype(np.uint8)


def generate(root=None):
    root=Path(root or Path(__file__).resolve().parents[1]/'assets/textures')
    root.mkdir(parents=True,exist_ok=True)
    n=256; y,x=np.mgrid[0:n,0:n]/n
    # All component frequencies are integral, hence the edges tile seamlessly.
    fine=(np.sin(2*np.pi*(61*x+43*y))+np.sin(2*np.pi*(47*x-67*y)))*.5
    tiles={
        'paint':.97+.008*fine,
        'rubber':.92+.04*fine,
        'metal':.94+.032*np.sin(2*np.pi*y*120)+.006*fine,
        'grip':.85+.075*np.cos(2*np.pi*x*32)*np.cos(2*np.pi*y*32)+.03*fine,
    }
    for name,pixels in tiles.items():
        rgb=np.repeat(np.clip(pixels[...,None]*255,0,255),3,axis=2).astype(np.uint8)
        Image.fromarray(rgb).save(root/(name+'.png'))
    Image.fromarray(water_pixels()).save(root/'water.png')
    yy,xx=np.mgrid[-1:1:complex(n),0:1:complex(n)]
    width=.15+.75*xx
    foam=np.exp(-(yy/width)**4)*(1-xx)**1.4
    ripples=.5+.5*np.sin(54*xx+7*yy)
    alpha=np.clip(foam*(.18+.38*ripples)*255,0,255).astype(np.uint8)
    wake=np.empty((n,n,4),dtype=np.uint8)
    wake[:,:,:3]=np.array([210,232,235]); wake[:,:,3]=alpha
    Image.fromarray(wake).save(root/'wake.png')


if __name__=='__main__': generate()
