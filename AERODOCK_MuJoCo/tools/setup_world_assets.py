"""Idempotently add scenery materials and a small contact pool to the boat MJCF."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]


def noise(size,scale,seed):
    """Periodic multiscale noise without the obvious sine-grid appearance."""
    rng=np.random.default_rng(seed)
    field=rng.normal(size=(size,size));fy,fx=np.meshgrid(np.fft.fftfreq(size),np.fft.fftfreq(size),indexing='ij')
    spectrum=np.fft.fft2(field)*np.exp(-(fx*fx+fy*fy)*(scale*size)**2)
    value=np.fft.ifft2(spectrum).real;value-=value.mean()
    return value/max(value.std(),1e-6)


def improved_tiles(size=512):
    y,x=np.mgrid[0:size,0:size]/size
    broad=noise(size,.065,71);mid=noise(size,.019,91);fine=noise(size,.003,17)
    rng=np.random.default_rng(12345)
    mix=lambda color,variation:np.clip(np.array(color)[None,None,:]+variation[...,None],0,255).astype(np.uint8)
    tiles={
      'sand':mix([185,170,137],6*broad+4*mid+3*fine),
      'wet_sand':mix([122,119,101],4*broad+3*mid+2*fine),
      'grass':mix([88,108,57],12*broad+7*mid+5*fine),
      'grass_macro':mix([94,111,65],18*broad+11*mid),
      'gravel':mix([134,132,123],8*broad+9*mid+3*fine),
      'rock':mix([117,120,117],12*broad+8*mid+3*fine),
      'rock_cliff':mix([132,133,124],17*broad+9*mid+3*fine),
      'rock_wet':mix([64,73,69],9*broad+6*mid+3*fine),
      'concrete':mix([156,154,143],6*broad+4*mid+2*fine),
      'asphalt':mix([59,64,65],3*broad+3*mid+3*fine),
      'foliage':mix([70,100,45],13*broad+12*mid+9*fine),
      'roof':mix([125,68,48],5*broad+4*mid+3*fine),
      'pavers':mix([172,165,149],5*broad+4*mid+2*fine),
      'quay':mix([138,137,124],9*broad+7*mid+3*fine)}
    # Sparse individual grains/pebbles, with wrapped copies for seamless edges.
    for name,count,rmin,rmax in [('gravel',2200,2,8),('sand',1600,.3,1.4),('foliage',1100,1.5,5)]:
        image=Image.fromarray(tiles[name]);draw=ImageDraw.Draw(image)
        for _ in range(count):
            px,py=rng.uniform(0,size,2);rx,ry=rng.uniform(rmin,rmax,2)
            level=int(rng.uniform(-28,24));base=np.array([134,132,123] if name=='gravel' else [185,170,137] if name=='sand' else [70,100,45])
            color=tuple(np.clip(base+level,0,255).astype(int))
            for ox in (-size,0,size):
                for oy in (-size,0,size):
                    if -rx<px+ox<size+rx and -ry<py+oy<size+ry:
                        draw.ellipse((px+ox-rx,py+oy-ry,px+ox+rx,py+oy+ry),fill=color)
        tiles[name]=np.array(image)
    # Block courses and roof tile seams are textures, not extra 3-D objects.
    mortar=((y*6)%1<.017)|(((x*4+(np.floor(y*6)%2)*.5)%1)<.012)
    tiles['quay'][mortar]=[83,87,83]
    damp=np.exp(-((y-.5)/.22)**2)*.32
    tiles['quay']=np.uint8(tiles['quay']*(1-damp[...,None]))
    joints=((x*8)%1<.023)|((y*8)%1<.023)
    tiles['pavers'][joints]=[124,126,117]
    roof_joints=((x*16)%1<.06)|((y*12)%1<.04)
    tiles['roof'][roof_joints]=[89,53,42]
    cracks=np.abs(mid-.35*broad)<.04
    tiles['rock'][cracks]=np.uint8(tiles['rock'][cracks]*.66)
    # Geological layers and broken fissures, with organic domain warping.
    layers=np.sin(2*np.pi*(y*9+.12*broad+.06*np.sin(2*np.pi*x*2)))
    tiles['rock_cliff']=np.uint8(np.clip(tiles['rock_cliff'].astype(float)+layers[...,None]*10,0,255))
    seams=np.abs(np.sin(2*np.pi*(y*9+.12*broad)))<.075
    fissures=np.abs(np.sin(2*np.pi*(x*7+.16*mid))+.28*broad)<.025
    tiles['rock_cliff'][seams|fissures]=np.uint8(tiles['rock_cliff'][seams|fissures]*.74)
    tiles['rock_wet'][cracks]=np.uint8(tiles['rock_wet'][cracks]*.63)
    # Additional native, deterministic facade families alongside the generated
    # harbor plaster texture. Tiles represent 4 bays x 4 storeys, 12 metres.
    for name,color in [('facade_brick',[158,108,78]),('facade_modern',[183,191,186])]:
        pixels=mix(color,4*broad+3*fine)
        if name=='facade_brick':
            brick=((y*48)%1<.08)|(((x*32+(np.floor(y*48)%2)*.5)%1)<.025)
            pixels[brick]=[178,165,142]
        wx=(x*4)%1;wy=(y*4)%1
        frame=(wx>.22)&(wx<.78)&(wy>.17)&(wy<.8)
        glass=(wx>.25)&(wx<.75)&(wy>.20)&(wy<.77)
        pixels[frame]=[207,201,185] if name=='facade_brick' else [89,105,108]
        glass_pixels=mix([57,77,86],4*broad+2*mid)
        pixels[glass]=glass_pixels[glass]
        mullion=(np.abs(wx-.5)<.01)&glass;pixels[mullion]=[166,174,171]
        tiles[name]=pixels
    return tiles

def setup():
    root=ET.parse(ROOT/'models/boat.xml');asset=root.getroot().find('asset');wb=root.getroot().find('worldbody')
    size=256;y,x=np.mgrid[0:size,0:size]/size
    grain=(np.sin(2*np.pi*(61*x+43*y))+np.sin(2*np.pi*(47*x-67*y)))*.5
    coarse=(np.sin(2*np.pi*(7*x+5*y))+np.cos(2*np.pi*(4*x-9*y)))*.5
    patterns={
      'sand':np.array([.76,.69,.51])[None,None,:]*(1+.05*grain+.03*coarse)[...,None],
      'grass':np.array([.31,.42,.20])[None,None,:]*(1+.14*grain+.13*coarse)[...,None],
      'gravel':np.array([.56,.54,.49])[None,None,:]*(1+.19*grain+.15*coarse)[...,None],
      'rock':np.array([.52,.51,.47])[None,None,:]*(1+.08*grain+.18*coarse)[...,None],
      'concrete':np.array([.66,.66,.62])[None,None,:]*(1+.045*grain+.04*coarse)[...,None],
      'asphalt':np.array([.27,.29,.30])[None,None,:]*(1+.1*grain)[...,None],
      'facade':np.repeat((.77+.015*grain)[...,None],3,axis=2)}
    windows=((x*4)%1>.2)&((x*4)%1<.8)&((y*4)%1>.2)&((y*4)%1<.8)
    patterns['facade'][windows]=[.25,.38,.43]
    patterns.update({name:rgb/255 for name,rgb in improved_tiles().items()})
    for name,pixels in patterns.items():
        filename='terrain_'+name+'.png'
        Image.fromarray(np.uint8(np.clip(pixels*255,0,255))).save(ROOT/'assets/textures'/filename)
        if asset.find("texture[@name='tex_terrain_%s']"%name) is None:
            ET.SubElement(asset,'texture',name='tex_terrain_'+name,type='2d',file=filename)
        if asset.find("material[@name='terrain_%s']"%name) is None:
            ET.SubElement(asset,'material',name='terrain_'+name,texture='tex_terrain_'+name,
                          texuniform='true',texrepeat='1 1' if name=='facade' else '2 2',
                          rgba='1 1 1 1',specular='.03',shininess='.05')
    if (ROOT/'assets/textures/harbor_facade.png').exists():
        asset.find("texture[@name='tex_terrain_facade']").set('file','harbor_facade.png')
    if (ROOT/'assets/textures/rock_cliff_photo.png').exists():
        asset.find("texture[@name='tex_terrain_rock_cliff']").set('file','rock_cliff_photo.png')
    if asset.find("material[@name='terrain_rock_boulder']") is None:
        ET.SubElement(asset,'material',name='terrain_rock_boulder',texture='tex_terrain_rock',
                      texuniform='true',texrepeat='2 2',rgba='1 1 1 1',specular='.03',shininess='.05')
    water_material=asset.find("material[@name='water_mat']")
    if water_material is not None:water_material.set('texrepeat','.045 .045')
    for i in range(16):
        if wb.find("body[@name='shore_proxy_%d']"%i) is not None:continue
        body=ET.SubElement(wb,'body',name=f'shore_proxy_{i}',mocap='true',pos='0 0 -50')
        ET.SubElement(body,'geom',name=f'shore_contact_{i}',type='box',size='2 1 5',
                      rgba='0 0 0 0',group='5',contype='0',conaffinity='0',
                      friction='.5 .01 .001',solref='.03 1')
    # Fixed-capacity GPU patch buffers. They are assets only, not physics geoms.
    # Unique vertices/UVs/normals keep compiler deduplication from shrinking them.
    meshdir=ROOT/'assets/meshes';meshdir.mkdir(exist_ok=True)
    lines=[]
    for i in range(384):
        face=i//3;corner=i%3;x=(face%16)*.01;y=(face//16)*.01
        px=x+(.003 if corner==1 else 0);py=y+(.003 if corner==2 else 0)
        lines.append(f'v {px:.7f} {py:.7f} 0')
    for i in range(384):lines.append(f'vt {i/500:.7f} {i/700:.7f}')
    for i in range(384):
        nx=i*1e-5;ny=i*2e-5;nz=np.sqrt(1-nx*nx-ny*ny)
        lines.append(f'vn {nx:.8f} {ny:.8f} {nz:.8f}')
    for i in range(128):
        ids=[3*i+j+1 for j in range(3)]
        lines.append('f '+' '.join(f'{j}/{j}/{j}' for j in ids))
    (meshdir/'scenery_buffer.obj').write_text('\n'.join(lines)+'\n')
    for i in range(256):
        if asset.find("mesh[@name='scenery_buffer_%d']"%i) is None:
            ET.SubElement(asset,'mesh',name=f'scenery_buffer_{i}',file='scenery_buffer.obj',
                          inertia='shell',maxhullvert='4')
    ET.indent(root,space='  ');root.write(ROOT/'models/boat.xml',encoding='utf-8',xml_declaration=True)

if __name__=='__main__':setup()
