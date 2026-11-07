"""Bake the neutral connected body into one portable material; workspace only."""
from pathlib import Path
import bpy,json,math,heapq,time
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/Kliff-Anatomy-Materials-0.5';TEX=OUT/'textures';TEX.mkdir(parents=True,exist_ok=True)
progress=ROOT/'work/anatomy-material-bake-status.json';started=time.time()
def status(stage,**extra):
 progress.write_text(json.dumps({'stage':stage,'elapsed_seconds':round(time.time()-started,1),**extra},indent=2));print('ATLAS_STAGE '+stage,flush=True)
status('loading')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Anatomy-Authoring-0.4/Kliff-Neutral-Anatomy-Controls.blend'),load_ui=False,use_scripts=False)
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
ob=bpy.data.objects['Kliff neutral body - connected topology prototype'];mesh=ob.data
original_count=len(mesh.vertices);original_positions=np.array([tuple(v.co) for v in mesh.vertices]);original_groups=[[(g.group,g.weight) for g in v.groups] for v in mesh.vertices]
for i,mat in enumerate(mesh.materials):mesh.materials[i]=mat.copy();mesh.materials[i].name='Atlas source '+str(i)
materials=list(mesh.materials)
# Pin implicit UV inputs before making the bake UV active.
def pin_uv(tree,name,seen):
 if tree.as_pointer() in seen:return
 seen.add(tree.as_pointer());uvnode=None
 def node():
  nonlocal uvnode
  if uvnode is None:uvnode=tree.nodes.new('ShaderNodeUVMap');uvnode.uv_map=name
  return uvnode
 for n in list(tree.nodes):
  if n.type=='GROUP':n.node_tree=n.node_tree.copy();pin_uv(n.node_tree,name,seen)
  elif n.type=='UVMAP' and not n.uv_map:n.uv_map=name
  elif n.type=='TEX_IMAGE' and not n.inputs['Vector'].is_linked:tree.links.new(node().outputs['UV'],n.inputs['Vector'])
  elif n.type=='TEX_COORD':
   for link in list(n.outputs['UV'].links):tree.links.new(node().outputs['UV'],link.to_socket)
  elif n.type=='NORMAL_MAP' and not n.uv_map:n.uv_map=name
pin_uv(materials[0].node_tree,'Original game UV',set());pin_uv(materials[1].node_tree,'Penis UV Map',set())

status('building shared colour transition')
edge_materials={};neighbors=[[] for _ in mesh.vertices]
for edge in mesh.edges:
 a,b=edge.vertices;length=(mesh.vertices[a].co-mesh.vertices[b].co).length;neighbors[a].append((b,length));neighbors[b].append((a,length))
for poly in mesh.polygons:
 for edge in poly.edge_keys:edge_materials.setdefault(tuple(sorted(edge)),set()).add(poly.material_index)
boundary={i for edge,mats in edge_materials.items() if len(mats)>1 for i in edge}
assert len(boundary)>=100,len(boundary)
dist=[float('inf')]*len(mesh.vertices);heap=[]
for i in boundary:dist[i]=0.;heapq.heappush(heap,(0.,i))
while heap:
 d,i=heapq.heappop(heap)
 if d!=dist[i] or d>.028:continue
 for j,length in neighbors[i]:
  nd=d+length
  if nd<dist[j]:dist[j]=nd;heapq.heappush(heap,(nd,j))
reference=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text())['parts'][2]
points=[Vector((v[0],-v[2],v[1])) for v in reference['vertices']];surface=BVHTree.FromPolygons(points,reference['faces'])
image=bpy.data.images['cd_phm_00_nude_00_0001.png'];width,height=image.size;pixels=np.asarray(image.pixels[:],dtype=float).reshape(height,width,4)
def skin_color(point):
 hit,n,face,d=surface.find_nearest(point);ids=reference['faces'][face]
 uv=barycentric_transform(hit,*[points[i] for i in ids],*[Vector((*reference['uvs'][i],0)) for i in ids])
 x=max(0,min(width-1,int(round(uv.x*(width-1)))));y=max(0,min(height-1,int(round(uv.y*(height-1)))))
 rgb=pixels[y,x,:3];linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4);return (*linear.tolist(),1.)
mask=mesh.color_attributes['Kliff seam mask'];color=mesh.color_attributes['Kliff seam color'];patch_count=0
for i,v in enumerate(mesh.vertices):
 t=max(0.,1.-dist[i]/.025);w=t*t*(3-2*t);mask.data[i].color=(w,w,w,1)
 if w>0:color.data[i].color=skin_color(v.co);patch_count+=1
tree=materials[0].node_tree;image_node=next(n for n in tree.nodes if n.type=='TEX_IMAGE');bs=next(n for n in tree.nodes if n.type=='BSDF_PRINCIPLED')
color_node=tree.nodes.new('ShaderNodeVertexColor');color_node.layer_name='Kliff seam color'
mask_node=tree.nodes.new('ShaderNodeVertexColor');mask_node.layer_name='Kliff seam mask'
mix=tree.nodes.new('ShaderNodeMixRGB');tree.links.new(mask_node.outputs['Color'],mix.inputs[0]);tree.links.new(image_node.outputs['Color'],mix.inputs[1]);tree.links.new(color_node.outputs['Color'],mix.inputs[2]);tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
body_color=mix.outputs[0]
anatomy_tree=materials[1].node_tree;anatomy_color=next(n for n in anatomy_tree.nodes if n.type=='MIX_RGB' and n.inputs[2].is_linked).outputs[0]
anatomy_rough=next(n for n in anatomy_tree.nodes if n.type=='MIX_RGB' and not n.inputs[2].is_linked).outputs[0]

status('creating shared UV atlas')
for obj in bpy.context.selected_objects:obj.select_set(False)
ob.select_set(True);bpy.context.view_layer.objects.active=ob
uv=mesh.uv_layers.new(name='GameAtlas');mesh.uv_layers.active=uv;uv.active_render=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.007);bpy.ops.object.mode_set(mode='OBJECT')
mesh=ob.data;uv=mesh.uv_layers['GameAtlas']
coords=np.array([tuple(loop.uv) for loop in uv.data]);assert np.isfinite(coords).all();low=coords.min(axis=0);high=coords.max(axis=0);span=float(max(high-low));assert span>.1
for loop in uv.data:loop.uv=((loop.uv.x-low[0])/span*.984+.008,(loop.uv.y-low[1])/span*.984+.008)
assert all(0<=x<=1 for loop in uv.data for x in loop.uv)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=16
original_outputs=[]
for mat in materials:
 output=next(n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL');original_outputs.append(output)
 for link in list(output.inputs['Displacement'].links):mat.node_tree.links.remove(link)
def bake_emit(label,sockets,space):
 status('baking '+label)
 image=bpy.data.images.new('Kliff atlas '+label,width=4096,height=4096,alpha=True);image.colorspace_settings.name=space
 nodes=[]
 for mat,output,socket in zip(materials,original_outputs,sockets):
  tr=mat.node_tree;em=tr.nodes.new('ShaderNodeEmission')
  if socket is None:em.inputs['Color'].default_value=(.64,.64,.64,1)
  else:tr.links.new(socket,em.inputs['Color'])
  tr.links.new(em.outputs[0],output.inputs['Surface']);target=tr.nodes.new('ShaderNodeTexImage');target.image=image;tr.nodes.active=target;nodes.append((tr,target,em))
 bpy.ops.object.bake(type='EMIT',uv_layer='GameAtlas')
 image.filepath_raw=str(TEX/(label+'.png'));image.file_format='PNG';image.save();image.pack()
 for tr,target,em in nodes:tr.nodes.remove(target);tr.nodes.remove(em)
 return image
base=bake_emit('BaseColor',[body_color,anatomy_color],'sRGB')
rough=bake_emit('Roughness',[None,anatomy_rough],'Non-Color')

status('preparing tangent normal bake')
# Reconstruct the preserved game's two-channel body normal. Its game-side Y convention is unverified.
tr=materials[0].node_tree;tex=tr.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'work/kliff-skin/cd_phm_00_nude_00_0001_n.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
uvnode=tr.nodes.new('ShaderNodeUVMap');uvnode.uv_map='Original game UV';tr.links.new(uvnode.outputs['UV'],tex.inputs['Vector']);split=tr.nodes.new('ShaderNodeSeparateColor');tr.links.new(tex.outputs['Color'],split.inputs[0])
def math_node(operation,a=None,b=None):
 n=tr.nodes.new('ShaderNodeMath');n.operation=operation
 for i,x in enumerate((a,b)):
  if x is not None:
   if isinstance(x,(float,int)):n.inputs[i].default_value=x
   else:tr.links.new(x,n.inputs[i])
 return n.outputs[0]
x=math_node('SUBTRACT',math_node('MULTIPLY',split.outputs['Red'],2),1);y=math_node('SUBTRACT',math_node('MULTIPLY',split.outputs['Green'],2),1)
z=math_node('SQRT',math_node('MAXIMUM',math_node('SUBTRACT',1,math_node('ADD',math_node('MULTIPLY',x,x),math_node('MULTIPLY',y,y))),0))
encoded_z=math_node('ADD',math_node('MULTIPLY',z,.5),.5);combine=tr.nodes.new('ShaderNodeCombineColor');tr.links.new(split.outputs['Red'],combine.inputs['Red']);tr.links.new(split.outputs['Green'],combine.inputs['Green']);tr.links.new(encoded_z,combine.inputs['Blue'])
normal=tr.nodes.new('ShaderNodeNormalMap');normal.uv_map='Original game UV';tr.links.new(combine.outputs[0],normal.inputs['Color']);tr.links.new(normal.outputs[0],bs.inputs['Normal']);tr.links.new(bs.outputs[0],original_outputs[0].inputs['Surface'])
tr=materials[1].node_tree;group=next(n for n in tr.nodes if n.type=='GROUP');geometry=tr.nodes.new('ShaderNodeNewGeometry');dot=tr.nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT'
disp=next(n for n in tr.nodes if n.type=='VECT_MATH' and n.operation=='SCALE');tr.links.new(disp.outputs['Vector'],dot.inputs[0]);tr.links.new(geometry.outputs['Normal'],dot.inputs[1]);bump=tr.nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=1.;tr.links.new(dot.outputs['Value'],bump.inputs['Height'])
pbr=tr.nodes.new('ShaderNodeBsdfPrincipled');tr.links.new(anatomy_color,pbr.inputs['Base Color']);tr.links.new(anatomy_rough,pbr.inputs['Roughness']);tr.links.new(bump.outputs[0],pbr.inputs['Normal']);tr.links.new(pbr.outputs[0],original_outputs[1].inputs['Surface'])
normal_image=bpy.data.images.new('Kliff atlas Normal',width=4096,height=4096,alpha=True);normal_image.colorspace_settings.name='Non-Color';targets=[]
for mat in materials:
 node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=normal_image;mat.node_tree.nodes.active=node;targets.append((mat.node_tree,node))
status('baking Normal');bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',normal_r='POS_X',normal_g='POS_Y',normal_b='POS_Z',uv_layer='GameAtlas')
normal_image.filepath_raw=str(TEX/'Normal.png');normal_image.file_format='PNG';normal_image.save();normal_image.pack()
for tr,target in targets:tr.nodes.remove(target)

status('building single baked material')
material=bpy.data.materials.new('Kliff connected body - baked atlas');material.use_nodes=True;tr=material.node_tree;pbr=tr.nodes['Principled BSDF'];pbr.inputs['Subsurface Weight'].default_value=.06
uvnode=tr.nodes.new('ShaderNodeUVMap');uvnode.uv_map='GameAtlas'
for label,image,socket in [('BaseColor',base,'Base Color'),('Roughness',rough,'Roughness')]:
 n=tr.nodes.new('ShaderNodeTexImage');n.name=label;n.image=image;tr.links.new(uvnode.outputs[0],n.inputs[0]);tr.links.new(n.outputs['Color'],pbr.inputs[socket])
n=tr.nodes.new('ShaderNodeTexImage');n.name='Normal';n.image=normal_image;tr.links.new(uvnode.outputs[0],n.inputs[0]);normal=tr.nodes.new('ShaderNodeNormalMap');normal.uv_map='GameAtlas';tr.links.new(n.outputs[0],normal.inputs['Color']);tr.links.new(normal.outputs[0],pbr.inputs['Normal'])
mesh.materials.clear();mesh.materials.append(material)
for p in mesh.polygons:p.material_index=0
assert len(mesh.vertices)==original_count and np.array_equal(original_positions,np.array([tuple(v.co) for v in mesh.vertices]))
assert original_groups==[[(g.group,g.weight) for g in v.groups] for v in mesh.vertices]
maps=[]
for label,image in [('BaseColor',base),('Roughness',rough),('Normal',normal_image)]:
 values=np.asarray(image.pixels[:],dtype=np.float32).reshape(-1,4);assert np.isfinite(values).all();covered=values[:,3]>.9;assert covered.sum()>100000
 maps.append({'name':label,'width':4096,'height':4096,'covered_pixels':int(covered.sum()),'covered_RGB_min':values[covered,:3].min(axis=0).tolist(),'covered_RGB_max':values[covered,:3].max(axis=0).tolist()})
scene.render.resolution_x=1000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.cycles.samples=24
for obj in bpy.data.objects:
 if obj.type=='ARMATURE':obj.hide_render=True
target=Vector((0,.08,.91));camera=scene.camera
if camera is None:
 camera=bpy.data.objects.new('Material inspection camera',bpy.data.cameras.new('Material inspection camera'));scene.collection.objects.link(camera);scene.camera=camera
camera.data.type='ORTHO';camera.data.ortho_scale=.66;camera.location=(1.5,3,1.07);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/'Atlas-Material-Review.png')
for light in [o for o in bpy.data.objects if o.type=='LIGHT']:bpy.data.objects.remove(light,do_unlink=True)
for name,location,power,size in [('Key',(-1.5,2,2),280,2),('Fill',(2,1,1.2),140,2),('Rim',(0,-2,2),220,2)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=location;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.12,.12,.12,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
status('rendering material review');bpy.ops.render.render(write_still=True)
if ob.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
rig=bpy.data.objects.get('Anatomy fitting controls - authoring only')
if rig:
 for obj in bpy.context.selected_objects:obj.select_set(False)
 rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='POSE')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-Neutral-Anatomy-Atlas.blend'))
report={'stage':'Portable single-material atlas review; game material binding unverified','date':'2026-10-30','maps':maps,'seam_boundary_vertices':len(boundary),'colour_transition_vertices':patch_count,'seam_transition_width_m':.025,'geometry_unchanged':True,'original_skin_and_authoring_weights_unchanged':True,'material_slots_after':len(mesh.materials),'source':'Preserved source shader and local game reference textures','limitations':['Body normal RG channels interpreted as tangent XY; game Y convention unverified.','Anatomy normal approximates the outward component of vector displacement; tangential displacement is not reproduced.','Game packed material/mask textures and current mod-manager archive mapping remain unverified.','No installed game files changed; clothing visibility and runtime physics remain unfinished.']}
(OUT/'Material-Validation.json').write_text(json.dumps(report,indent=2));status('finished',output=str(OUT))
