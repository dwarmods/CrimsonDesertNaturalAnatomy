import bpy, bmesh, math, json, heapq
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'outputs/Kliff-Anatomy-Model-v0.2'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Kliff-source-fit.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene
source=bpy.data.objects['Kliff anatomy - ThineCrawler source rig']
body=bpy.data.objects['CD_PHM_00_Nude_0001']
dg=bpy.context.evaluated_depsgraph_get()
ev=source.evaluated_get(dg)
mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
ob=bpy.data.objects.new('Kliff anatomy - fitted export mesh',mesh)
collection=bpy.data.collections.new('FITTED MODEL - neutral pose')
scene.collection.children.link(collection);collection.objects.link(ob)
ob.matrix_world=source.matrix_world.copy()
for name in ('source_author','source_url','license'):ob[name]=source[name]
ob['purpose']='Neutral fitted mesh; CC BY-SA 4.0 adaptation; static pelvis binding.'
source.hide_render=True;source.hide_set(True)
mesh.uv_layers.active=mesh.uv_layers['Penis UV Map']
mesh.uv_layers['Penis UV Map'].active_render=True
bvh=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
boundary={v.index for e in bm.edges if e.is_boundary for v in e.verts}
assert len(boundary)==128,len(boundary)
world=ob.matrix_world.copy();inv=world.inverted()
pos=[world @ v.co for v in mesh.vertices]
# Geodesic distance from the attachment loop avoids affecting nearby opposing
# surfaces or the distal end when blending the seam.
dist=[float('inf')]*len(pos);nearest=[-1]*len(pos);heap=[]
for idx in boundary:dist[idx]=0;nearest[idx]=idx;heapq.heappush(heap,(0,idx))
while heap:
    d,i=heapq.heappop(heap)
    if d!=dist[i] or d>.028:continue
    for edge in bm.verts[i].link_edges:
        j=edge.other_vert(bm.verts[i]).index;nd=d+(pos[j]-pos[i]).length
        if nd<dist[j]:dist[j]=nd;nearest[j]=nearest[i];heapq.heappush(heap,(nd,j))
delta={}
for i in boundary:
    p=pos[i];hit,n,face,d=bvh.ray_cast(Vector((p.x,.5,p.z)),Vector((0,-1,0)))
    if hit is None:raise RuntimeError('Root projection missed body')
    delta[i]=hit-n*.0007-p
for i,v in enumerate(mesh.vertices):
    if dist[i]<.022:
        t=max(0,1-dist[i]/.022);w=t*t*(3-2*t)
        v.co=inv @ (pos[i]+delta[nearest[i]]*w)
mesh.update()

# Sample the actual body texture at the closest triangle, in linear color.
image=bpy.data.images['cd_phm_00_nude_00_0001.png']
pixels=list(image.pixels);width,height=image.size
uv=body.data.uv_layers.active
def sampled_skin(p):
    loc,n,fi,d=bvh.find_nearest(p);poly=body.data.polygons[fi]
    vs=[body.data.vertices[i].co for i in poly.vertices]
    uvs=[Vector((*uv.data[li].uv,0)) for li in poly.loop_indices]
    t=barycentric_transform(loc,vs[0],vs[1],vs[2],uvs[0],uvs[1],uvs[2])
    x=max(0,min(width-1,round(t.x*(width-1))));y=max(0,min(height-1,round(t.y*(height-1))))
    k=(y*width+x)*4
    # Image pixel access returns encoded file values; shader color attributes
    # are linear. Match the image texture node's sRGB decoding explicitly.
    def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
    return tuple(linear(c) for c in pixels[k:k+3])+(1,)
color=mesh.color_attributes.new(name='Kliff seam color',type='FLOAT_COLOR',domain='POINT')
mask=mesh.color_attributes.new(name='Kliff seam mask',type='FLOAT_COLOR',domain='POINT')
for i,v in enumerate(mesh.vertices):
    t=max(0,1-dist[i]/.025);w=t*t*(3-2*t)
    mask.data[i].color=(w,w,w,1)
    color.data[i].color=sampled_skin(world @ v.co) if w>0 else (0,0,0,1)

# A shared tangent direction at the open seam reduces the shading discontinuity.
normal_matrix=world.to_3x3().inverted().transposed()
inv_normal=normal_matrix.inverted()
custom=[]
for i,v in enumerate(mesh.vertices):
    n=(normal_matrix @ v.normal).normalized()
    if dist[i]<.008:
        _,bn,_,_=bvh.find_nearest(world @ v.co)
        t=max(0,1-dist[i]/.008);w=t*t*(3-2*t)
        n=n.lerp(bn,w).normalized()
    custom.append(tuple((inv_normal @ n).normalized()))
mesh.normals_split_custom_set_from_vertices(custom)

old=bpy.data.materials['Realistic Penis Shader'];oldgroup=old.node_tree.nodes['Realistic Penis Shader']
group=oldgroup.node_tree.copy();group.name='ThineCrawler shader with bake outputs'
group.interface.new_socket(name='Bake Color',in_out='OUTPUT',socket_type='NodeSocketColor')
group.interface.new_socket(name='Bake Roughness',in_out='OUTPUT',socket_type='NodeSocketFloat')
gout=next(n for n in group.nodes if n.type=='GROUP_OUTPUT')
group.links.new(group.nodes['Reroute.002'].outputs[0],gout.inputs['Bake Color'])
group.links.new(group.nodes['Clamp'].outputs[0],gout.inputs['Bake Roughness'])
mat=bpy.data.materials.new('Fitted anatomy - source shader and Kliff seam');mat.use_nodes=True
tree=mat.node_tree;tree.nodes.clear()
gn=tree.nodes.new('ShaderNodeGroup');gn.node_tree=group
for s in oldgroup.inputs:
    if hasattr(s,'default_value'):gn.inputs[s.name].default_value=s.default_value
gn.inputs['Overall Roughness'].default_value=.95
gn.inputs['Glans Roughness'].default_value=.8
gn.inputs['Subsurface Scale'].default_value=.002
gn.inputs['Glans Subsurface Scale'].default_value=.004
cn=tree.nodes.new('ShaderNodeVertexColor');cn.layer_name=color.name
mn=tree.nodes.new('ShaderNodeVertexColor');mn.layer_name=mask.name
blend=tree.nodes.new('ShaderNodeMixRGB');blend.blend_type='MIX'
tree.links.new(mn.outputs['Color'],blend.inputs[0]);tree.links.new(gn.outputs['Bake Color'],blend.inputs[1]);tree.links.new(cn.outputs['Color'],blend.inputs[2])
rough=tree.nodes.new('ShaderNodeMixRGB');tree.links.new(mn.outputs['Color'],rough.inputs[0]);tree.links.new(gn.outputs['Bake Roughness'],rough.inputs[1]);rough.inputs[2].default_value=(.64,.64,.64,1)
skin=tree.nodes.new('ShaderNodeBsdfPrincipled');skin.inputs['Roughness'].default_value=.64;skin.inputs['Subsurface Weight'].default_value=.06
tree.links.new(cn.outputs['Color'],skin.inputs['Base Color'])
mix=tree.nodes.new('ShaderNodeMixShader');tree.links.new(mn.outputs['Color'],mix.inputs[0]);tree.links.new(gn.outputs['Cycles'],mix.inputs[1]);tree.links.new(skin.outputs['BSDF'],mix.inputs[2])
out=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(mix.outputs[0],out.inputs['Surface'])
inverse=tree.nodes.new('ShaderNodeMath');inverse.operation='SUBTRACT';inverse.inputs[0].default_value=1;tree.links.new(mn.outputs['Color'],inverse.inputs[1])
disp=tree.nodes.new('ShaderNodeVectorMath');disp.operation='SCALE';tree.links.new(gn.outputs['Vector Displacement'],disp.inputs[0]);tree.links.new(inverse.outputs[0],disp.inputs['Scale']);tree.links.new(disp.outputs[0],out.inputs['Displacement'])
mesh.materials.clear();mesh.materials.append(mat)

# Export anchor from the actual game's pelvis bind matrix. Authoring rig remains
# available separately, but its custom bones are not presented as game bones.
data=json.loads((ROOT/'kliff-body.json').read_text());pelvis=next(b for b in data['bones'] if b['name']=='Bip01 Pelvis')
convert=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
bind=Matrix([pelvis['matrix'][i:i+4] for i in range(0,16,4)]).transposed()
arm=bpy.data.armatures.new('Original pelvis export anchor');anchor=bpy.data.objects.new('Kliff pelvis - static export anchor',arm);collection.objects.link(anchor)
bpy.ops.object.select_all(action='DESELECT');anchor.select_set(True);bpy.context.view_layer.objects.active=anchor;bpy.ops.object.mode_set(mode='EDIT')
bone=arm.edit_bones.new('Bip01 Pelvis');bone.matrix=convert @ bind @ convert.inverted();bone.length=.1
bpy.ops.object.mode_set(mode='OBJECT');anchor.select_set(False)
ob.vertex_groups.clear();vg=ob.vertex_groups.new(name='Bip01 Pelvis');vg.add(list(range(len(mesh.vertices))),1,'REPLACE')
am=ob.modifiers.new('Static original pelvis binding','ARMATURE');am.object=anchor
previous=ob.matrix_world.copy();ob.parent=anchor;ob.matrix_world=previous

# Texture bakes remove the procedural material dependency for interchange.
texdir=OUT/'textures';texdir.mkdir(exist_ok=True)
scene.render.engine='CYCLES';scene.cycles.samples=16
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=12
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
em=tree.nodes.new('ShaderNodeEmission');baked={}
for name,socket,space in [('BaseColor',blend.outputs[0],'sRGB'),('Roughness',rough.outputs[0],'Non-Color')]:
    im=bpy.data.images.new('Kliff anatomy '+name,width=2048,height=2048,alpha=False)
    im.colorspace_settings.name=space;target=tree.nodes.new('ShaderNodeTexImage');target.image=im;tree.nodes.active=target
    tree.links.new(socket,em.inputs['Color']);tree.links.new(em.outputs[0],out.inputs['Surface'])
    for link in list(out.inputs['Displacement'].links):tree.links.remove(link)
    bpy.ops.object.bake(type='EMIT')
    im.filepath_raw=str(texdir/f'{name}.png');im.file_format='PNG';im.save();im.pack();baked[name]=im
    tree.nodes.remove(target)
tree.links.new(mix.outputs[0],out.inputs['Surface']);tree.links.new(disp.outputs[0],out.inputs['Displacement'])
tree.nodes.remove(em)

# Store the authoring shader with the fit; a baked PBR duplicate is used for GLB.
bpy.context.view_layer.update()
check=bmesh.new();check.from_mesh(mesh)
report=dict(stage='Fitted Blender model; not an installable game mod',source_author='ThineCrawler',
    license='CC BY-SA 4.0',source_sha256='ac422bf36d0424384d325bb8e55b1a6f8d6bde798d38a4926eba33a0985e3c13',
    vertices=len(mesh.vertices),faces=len(mesh.polygons),boundary_vertices=len(boundary),
    zero_area_faces=sum(f.calc_area()<1e-12 for f in check.faces),
    nonmanifold_interior_edges=sum(not e.is_manifold and not e.is_boundary for e in check.edges),
    seam='Open attachment loop projected 0.7 mm inside Kliff body; color transition sampled from original body texture. Not welded.',
    skinning='100 percent original pelvis anchor; static attachment, not runtime physics',
    textures='2048px base color and roughness baked from source shader; source VDM remains in Blender shader',
    runtime_tested=False)
check.free();bm.free()
assert report['zero_area_faces']==0 and report['nonmanifold_interior_edges']==0
before=[ob.matrix_world @ v.co for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
anchor.pose.bones[0].location=(.01,0,0);bpy.context.view_layer.update()
after=[ob.matrix_world @ v.co for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
err=max(abs((a-b).length-.01) for a,b in zip(after,before));assert err<2e-5,err
anchor.pose.bones[0].location=(0,0,0);bpy.context.view_layer.update();report['pelvis_translation_max_error_m']=err

portable=bpy.data.materials.new('Anatomy baked PBR');portable.use_nodes=True
p=portable.node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.65
for key,socket in [('BaseColor','Base Color'),('Roughness','Roughness')]:
    n=portable.node_tree.nodes.new('ShaderNodeTexImage');n.image=baked[key];portable.node_tree.links.new(n.outputs['Color'],p.inputs[socket])
mesh.materials[0]=portable
ob.select_set(True);anchor.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.export_scene.gltf(filepath=str(OUT/'Kliff-anatomy-baked.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False)
mesh.materials[0]=mat
report['glb_limit']='Baked color and roughness only; procedural vector displacement detail is retained in the Blender scene, not represented in GLB.'
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

cam=scene.camera
def render(name,loc,target,scale):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(OUT/name);bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
scene.cycles.samples=32
render('fit-three-quarter.png',(1.8,3,1.15),(0,.08,.96),.61)
bpy.data.objects['CD_PHM_00_Nude_0001_Hand'].hide_render=True
render('fit-side.png',(3,1.1,1.02),(0,.06,.94),.51)
bpy.data.objects['CD_PHM_00_Nude_0001_Hand'].hide_render=False
render('fit-front.png',(0,3,1.00),(0,.06,.98),.70)
anchor.hide_set(True)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-anatomy-fit.blend'))
print(json.dumps(report,indent=2))
