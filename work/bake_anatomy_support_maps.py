"""Remap native packed channels without assuming their roughness/specular meanings."""
import bpy,json,time
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/Kliff-Anatomy-Materials-0.5';TEX=OUT/'textures'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Anatomy-Authoring-0.4/Kliff-Neutral-Anatomy-Controls.blend'),load_ui=False,use_scripts=False)
name='Kliff neutral body - connected topology prototype';zones=[p.material_index for p in bpy.data.objects[name].data.polygons]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Kliff-Neutral-Anatomy-Atlas.blend'),load_ui=False,use_scripts=False)
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
ob=bpy.data.objects[name];mesh=ob.data;portable=mesh.materials[0];assert len(zones)==len(mesh.polygons)
for obj in bpy.context.selected_objects:obj.select_set(False)
ob.select_set(True);bpy.context.view_layer.objects.active=ob
reference=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text())['parts'][2]
points=[Vector((v[0],-v[2],v[1])) for v in reference['vertices']];surface=BVHTree.FromPolygons(points,reference['faces']);sample_uv=[]
for v in mesh.vertices:
 point,n,fi,d=surface.find_nearest(v.co);ids=reference['faces'][fi]
 uv=barycentric_transform(point,*[points[i] for i in ids],*[Vector((*reference['uvs'][i],0)) for i in ids]);sample_uv.append(tuple(uv[:2]))
scene=bpy.context.scene;scene.cycles.samples=1;report=[]
for label,suffix in [('PackedMaterial','_sp'),('SkinMask','_m')]:
 image=bpy.data.images.load(str(ROOT/'work/kliff-skin'/('cd_phm_00_nude_00_0001'+suffix+'.png')),check_existing=True);image.colorspace_settings.name='Non-Color';width,height=image.size;pixels=np.array(image.pixels[:]).reshape(height,width,4)
 assert np.all(pixels[:,:,3]>.999),'Non-constant packed alpha needs a separate explicit bake'
 attr=mesh.color_attributes.new(name='Native '+label+' sample',type='FLOAT_COLOR',domain='POINT')
 for i,(u,v) in enumerate(sample_uv):
  x=max(0,min(width-1,int(round(u*(width-1)))));y=max(0,min(height-1,int(round(v*(height-1)))));attr.data[i].color=tuple(pixels[y,x,:3])+(1,)
 mesh.materials.clear()
 for zone in range(2):
  mat=bpy.data.materials.new(label+' bake '+str(zone));mat.use_nodes=True;mesh.materials.append(mat);tr=mat.node_tree;tr.nodes.clear()
  output=tr.nodes.new('ShaderNodeOutputMaterial');em=tr.nodes.new('ShaderNodeEmission');tr.links.new(em.outputs[0],output.inputs['Surface']);sample=tr.nodes.new('ShaderNodeVertexColor');sample.layer_name=attr.name
  if zone==0:
   texture=tr.nodes.new('ShaderNodeTexImage');texture.image=image;uv=tr.nodes.new('ShaderNodeUVMap');uv.uv_map='Original game UV';tr.links.new(uv.outputs[0],texture.inputs[0]);mask=tr.nodes.new('ShaderNodeVertexColor');mask.layer_name='Kliff seam mask';mix=tr.nodes.new('ShaderNodeMixRGB');tr.links.new(mask.outputs[0],mix.inputs[0]);tr.links.new(texture.outputs[0],mix.inputs[1]);tr.links.new(sample.outputs[0],mix.inputs[2]);tr.links.new(mix.outputs[0],em.inputs[0])
  else:tr.links.new(sample.outputs[0],em.inputs[0])
 for poly,zone in zip(mesh.polygons,zones):poly.material_index=zone
 result=bpy.data.images.new('Kliff atlas '+label,width=4096,height=4096,alpha=True);result.colorspace_settings.name='Non-Color'
 for mat in mesh.materials:
  target=mat.node_tree.nodes.new('ShaderNodeTexImage');target.image=result;mat.node_tree.nodes.active=target
 print('SUPPORT_BAKE '+label,flush=True);bpy.ops.object.bake(type='EMIT',uv_layer='GameAtlas')
 result.filepath_raw=str(TEX/(label+'.png'));result.file_format='PNG';result.save();result.pack()
 node=portable.node_tree.nodes.new('ShaderNodeTexImage');node.name='Native '+label+' export';node.label='Native packed channels - not interpreted by this PBR preview';node.image=result
 report.append({'map':label,'source_texture':image.filepath,'preserved_RGB_channels':True,'source_alpha_constant_one':True,'new_anatomy_parameters':'Sampled from nearby original body skin; no assumed packed channel reinterpretation.'})
mesh.materials.clear();mesh.materials.append(portable)
for poly in mesh.polygons:poly.material_index=0
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-Neutral-Anatomy-Atlas.blend'))
(OUT/'Native-Support-Maps.json').write_text(json.dumps({'maps':report,'native_material_calibration_verified':False,'game_modified':False},indent=2));print('SUPPORT_MAPS_READY')
