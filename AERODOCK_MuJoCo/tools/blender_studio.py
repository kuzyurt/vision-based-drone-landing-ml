"""Blender worker for render_stills.py; no edits to simulation assets."""
import json
import math
import os
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Vector

folder, output = map(Path, sys.argv[sys.argv.index('--')+1:])
records = json.loads((folder/'scene.json').read_text())
geometry = np.load(folder/'geometry.npz')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 192
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = .012
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 8
try:
    preferences = bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type = 'CUDA'
    preferences.get_devices()
    gpu = False
    for device in preferences.devices:
        device.use = device.type == 'CUDA'
        gpu |= device.use
    if gpu: scene.cycles.device = 'GPU'
except Exception as error:
    print('Using CPU rendering:', error, flush=True)
scene.render.resolution_x = int(os.environ.get('AERODOCK_RENDER_WIDTH','2560'))
scene.render.resolution_y = round(scene.render.resolution_x*5/8)
if scene.render.resolution_x < 1000: scene.cycles.samples = 32
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = -.4
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.78,.84,.93,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35


def linear(color):
    return tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in color)


materials = {}
def material(record):
    name, color = record['part'], record['color']
    cable = 'cable' in record['material'].lower() or 'hose' in record['material'].lower()
    silver = color == [.72,.77,.8]
    gold = color in ([.72,.51,.24], [.92,.72,.23])
    glass = name.endswith('Window')
    metal = .82 if silver or gold else 0
    roughness = .3 if silver else .28 if gold else .43 if cable else .42
    if name in ('HullShell','MainDeck') or 'SlidingLid' in name: roughness = .25
    if 'Grip' in name or 'Seal' in name or 'RubRail' in name: roughness = .72
    if 'Components' in name: roughness = .52
    key = (tuple(color),metal,roughness,record['textured'],glass)
    if key in materials: return materials[key]
    mat = bpy.data.materials.new(name + ' finish')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*linear(color),1)
    bsdf.inputs['Metallic'].default_value = metal
    bsdf.inputs['Roughness'].default_value = roughness
    if name in ('HullShell','MainDeck') or 'SlidingLid' in name:
        bsdf.inputs['Coat Weight'].default_value = .35
        bsdf.inputs['Coat Roughness'].default_value = .2
    if glass:
        bsdf.inputs['Base Color'].default_value = (.82,.9,.96,1)
        bsdf.inputs['Transmission Weight'].default_value = .94
        bsdf.inputs['IOR'].default_value = 1.46
        bsdf.inputs['Roughness'].default_value = .075
    bevel = nodes.new('ShaderNodeBevel')
    bevel.inputs['Radius'].default_value = .00055
    bevel.samples = 3
    # Interiors keep plain material finishes; only exterior surfaces receive
    # texture detail. World positions give constant physical texture scale.
    if record['textured']:
        coords = nodes.new('ShaderNodeNewGeometry')
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 850 if 'Grip' not in name else 500
        noise.inputs['Detail'].default_value = 2
        links.new(coords.outputs['Position'], noise.inputs['Vector'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .18
        bump.inputs['Distance'].default_value = .00012 if 'Grip' not in name else .00045
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bevel.outputs['Normal'], bump.inputs['Normal'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
        ramp = nodes.new('ShaderNodeMapRange')
        ramp.inputs['To Min'].default_value = roughness*.85
        ramp.inputs['To Max'].default_value = min(.9,roughness*1.15)
        links.new(noise.outputs['Fac'],ramp.inputs['Value'])
        links.new(ramp.outputs['Result'],bsdf.inputs['Roughness'])
    else:
        links.new(bevel.outputs['Normal'],bsdf.inputs['Normal'])
    materials[key] = mat
    return mat


objects = []
minimum_z = math.inf
for record in records:
    key = record['key']
    vertices, faces = geometry['v'+key], geometry['f'+key]
    # UV splits in the source export duplicate vertices. Join coincident
    # positions for continuous curved normals; retain sharp mechanical edges.
    vertices, inverse = np.unique(np.round(vertices,7),axis=0,return_inverse=True)
    faces = inverse[faces]
    minimum_z = min(minimum_z,float(vertices[:,2].min()))
    mesh = bpy.data.meshes.new(record['name'])
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()
    mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool))
    mesh.set_sharp_from_angle(angle=math.radians(35))
    obj = bpy.data.objects.new(record['name'],mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(material(record))
    objects.append((obj,record['hidden'],record['helper']))
print('Loaded %d CAD mesh pieces' % len(objects), flush=True)

# Neutral CAD studio floor, with a restrained metric reference grid.
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,minimum_z-.012))
floor = bpy.context.object
floor.name = 'Studio floor'
mat = bpy.data.materials.new('Neutral CAD surface')
mat.use_nodes = True
nodes, links = mat.node_tree.nodes,mat.node_tree.links
bsdf = nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.37,.41,.46,1)
bsdf.inputs['Roughness'].default_value = .82
coords = nodes.new('ShaderNodeNewGeometry')
separate = nodes.new('ShaderNodeSeparateXYZ')
links.new(coords.outputs['Position'],separate.inputs['Vector'])
lines = []
for axis in ('X','Y'):
    scale = nodes.new('ShaderNodeMath'); scale.operation='MULTIPLY'; scale.inputs[1].default_value=4
    fraction = nodes.new('ShaderNodeMath'); fraction.operation='FRACT'
    line = nodes.new('ShaderNodeMath'); line.operation='LESS_THAN'; line.inputs[1].default_value=.005
    links.new(separate.outputs[axis],scale.inputs[0]); links.new(scale.outputs[0],fraction.inputs[0]);links.new(fraction.outputs[0],line.inputs[0])
    lines.append(line)
combine = nodes.new('ShaderNodeMath');combine.operation='MAXIMUM'
links.new(lines[0].outputs[0],combine.inputs[0]);links.new(lines[1].outputs[0],combine.inputs[1])
mix = nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.37,.41,.46,1);mix.inputs[2].default_value=(.32,.36,.4,1)
links.new(combine.outputs[0],mix.inputs[0]);links.new(mix.outputs[0],bsdf.inputs['Base Color'])
floor.data.materials.append(mat)


def aim(obj, point):
    obj.rotation_euler = (Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()


def light(name,position,power,size,color):
    data = bpy.data.lights.new(name,'AREA');data.energy=power*.4;data.shape='DISK';data.size=size;data.color=color
    obj = bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=position;aim(obj,(0,0,.3))


light('Key softbox',(-2,-3,4.5),900,3,(1,.96,.9))
light('Cool fill',(1,3,3),650,2.5,(.85,.92,1))
light('Long edge reflection',(3,-1,2.7),950,2.2,(1,1,1))
light('Front fill',(-3,3,1.4),250,2,(1,1,1))
data = bpy.data.cameras.new('Studio camera')
camera = bpy.data.objects.new('Studio camera',data)
scene.collection.objects.link(camera)
scene.camera = camera
data.type='ORTHO';data.ortho_scale=3.55;data.lens=55
data.clip_start=.01;data.clip_end=300
camera.location=(-3.2,3.4,2.65);aim(camera,(0,0,.46))
output.mkdir(parents=True,exist_ok=True)
for filename,cutaway in (('boat_exterior.png',False),('boat_cutaway.png',True)):
    for obj,hidden,helper in objects: obj.hide_render=helper or (cutaway and hidden)
    scene.render.filepath=str(output/filename)
    bpy.ops.render.render(write_still=True)
    print('Saved',filename,flush=True)
