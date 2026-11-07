"""Neutral anatomical study: replace overlapping join with connected topology.

Workspace-only prototype. The source Blender shader is retained; this does not
claim PAC export, clothing integration, or runtime dynamics.
"""
import bpy,bmesh,json,math,heapq
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'neutral-body-rebuild';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'outputs/Kliff-Anatomy-Model-v0.2/Kliff-anatomy-fit.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene
ob=bpy.data.objects['Kliff anatomy - fitted export mesh']
body=bpy.data.objects['CD_PHM_00_Nude_0001']
original=json.loads((ROOT/'kliff-body.json').read_text())
part=original['parts'][2]
# Preserve the original game skin weights on the reference before topology work.
body.vertex_groups.clear()
for b in original['bones']:body.vertex_groups.new(name=b['name'])
for i,(slots,weights) in enumerate(zip(part['bone_indices'],part['bone_weights'])):
    total=sum(w for w in weights if w>0)
    for s,w in zip(slots,weights):
        if w>0:body.vertex_groups[original['palette'][s]].add([i],w/total,'REPLACE')
world=ob.matrix_world.copy();old_root=Vector((0,.122,.945));new_root=Vector((0,.118,.915))
for v in ob.data.vertices:v.co=new_root+(world@v.co-old_root)*1.20
ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
ob.data.update()
source_uv=ob.data.uv_layers['Penis UV Map']
shared_uv=ob.data.uv_layers.get('Original game UV') or ob.data.uv_layers.new(name='Original game UV')
for i,loop in enumerate(source_uv.data):shared_uv.data[i].uv=loop.uv
ob.data.uv_layers.active=shared_uv;shared_uv.active_render=True
body.data.calc_loop_triangles()
surface=BVHTree.FromPolygons([v.co for v in body.data.vertices],[p.vertices[:] for p in body.data.polygons])
def project(p):
    hit,n,fi,d=surface.ray_cast(Vector((p.x,.5,p.z)),Vector((0,-1,0)))
    if hit is None:raise RuntimeError('Body projection missed')
    return hit,n,fi
uv_original=body.data.uv_layers.active
original_triangles=[([body.data.vertices[i].co.copy() for i in p.vertices],[Vector((*uv_original.data[li].uv,0)) for li in p.loop_indices]) for p in body.data.polygons]
skin_image=bpy.data.images['cd_phm_00_nude_00_0001.png']
pixels=list(skin_image.pixels);width,height=skin_image.size
def skin_uv(p):
    loc,n,fi,d=surface.find_nearest(p)
    vs,uvs=original_triangles[fi]
    return barycentric_transform(loc,*vs[:3],*uvs[:3]).xy
def skin_color(p):
    uv=skin_uv(p);x=max(0,min(width-1,round(uv.x*(width-1))));y=max(0,min(height-1,round(uv.y*(height-1))))
    cs=pixels[4*(y*width+x):4*(y*width+x)+3]
    return tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in cs)+(1,)

bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table()
root_edges=[e for e in bm.edges if e.is_boundary]
root_verts={v for e in root_edges for v in e.verts}
assert len(root_edges)==128
# Expand only the attachment edge into a broad transition on the lower torso.
dist={v:float('inf') for v in bm.verts};owner={};heap=[]
for v in root_verts:dist[v]=0;owner[v]=v;heapq.heappush(heap,(0,v.index))
while heap:
    d,i=heapq.heappop(heap);v=bm.verts[i]
    if d!=dist[v] or d>.05:continue
    for edge in v.link_edges:
        q=edge.other_vert(v);nd=d+edge.calc_length()
        if nd<dist[q]:dist[q]=nd;owner[q]=owner[v];heapq.heappush(heap,(nd,q.index))
center=sum((v.co for v in root_verts),Vector())/len(root_verts)
delta={}
for v in root_verts:
    angle=math.atan2((v.co.z-center.z)/.022,(v.co.x-center.x)/.025)
    target=Vector((.039*math.cos(angle),0,center.z+.033*math.sin(angle)))
    hit,_,_=project(target);delta[v]=hit-v.co
for v in bm.verts:
    if dist[v]<.035:
        t=1-dist[v]/.035;v.co+=delta[owner[v]]*(t*t*(3-2*t))
    if dist[v]<.018:
        t=1-dist[v]/.018;hit,_,_=project(v.co)
        v.co.y=v.co.y*(1-t*t*(3-2*t))+hit.y*(t*t*(3-2*t))
root_positions=[v.co.copy() for v in root_verts]
bm.to_mesh(ob.data);bm.free();ob.data.update()
mask=ob.data.color_attributes['Kliff seam mask'];colors=ob.data.color_attributes['Kliff seam color']
# Recompute distances on the resulting mesh; no stale BMesh references survive.
bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table()
dist2=[float('inf')]*len(bm.verts);heap=[]
for e in bm.edges:
    if e.is_boundary:
        for v in e.verts:
            if dist2[v.index]!=0:dist2[v.index]=0;heapq.heappush(heap,(0,v.index))
while heap:
    d,i=heapq.heappop(heap)
    if d!=dist2[i] or d>.05:continue
    for e in bm.verts[i].link_edges:
        j=e.other_vert(bm.verts[i]).index;nd=d+e.calc_length()
        if nd<dist2[j]:dist2[j]=nd;heapq.heappush(heap,(nd,j))
bm.free()
for i,v in enumerate(ob.data.vertices):
    t=max(0,1-dist2[i]/.04);w=t*t*(3-2*t)
    mask.data[i].color=(w,w,w,1);colors.data[i].color=skin_color(v.co) if w else (0,0,0,1)
ob.data.normals_split_custom_set([(0,0,0)]*len(ob.data.loops))
ob.vertex_groups.clear()
for b in original['bones']:ob.vertex_groups.new(name=b['name'])
pelvis_id=next(b['index'] for b in original['bones'] if b['name']=='Bip01 Pelvis')
for i,v in enumerate(ob.data.vertices):
    blend=max(0,1-dist2[i]/.035);blend=blend*blend*(3-2*blend)
    weights={pelvis_id:1-blend}
    if blend:
        loc,n,fi,d=surface.find_nearest(v.co)
        ids=part['faces'][fi];tri=original_triangles[fi][0]
        bary=barycentric_transform(loc,*tri[:3],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        for vi,bw in zip(ids,bary):
            for slot,w in zip(part['bone_indices'][vi],part['bone_weights'][vi]):
                bi=original['palette'][slot];weights[bi]=weights.get(bi,0)+blend*max(0,bw)*w
    weights=dict(sorted(((bi,w) for bi,w in weights.items() if w>1e-6),key=lambda x:-x[1])[:6]);total=sum(weights.values())
    for bi,w in weights.items():ob.vertex_groups[bi].add([i],w/total,'REPLACE')

# Cut an opening in the body. Merge only exact coincident vertices so the UV
# borders do not masquerade as geometric holes; corner UVs remain distinct.
bb=bmesh.new();bb.from_mesh(body.data)
bmesh.ops.remove_doubles(bb,verts=list(bb.verts),dist=1e-6)
bb.normal_update()
cut=[f for f in bb.faces if (f.calc_center_median().x/.052)**2+((f.calc_center_median().z-center.z)/.044)**2<1 and f.calc_center_median().y>.03 and f.normal.y>.25]
assert cut,'No body patch found'
bmesh.ops.delete(bb,geom=cut,context='FACES')
loose=[v for v in bb.verts if not v.link_faces]
if loose:bmesh.ops.delete(bb,geom=loose,context='VERTS')
hole_edges=[e for e in bb.edges if e.is_boundary and abs(e.verts[0].co.x)<.09 and abs(e.verts[0].co.z-center.z)<.08 and e.verts[0].co.y>.02]
hole_verts={v for e in hole_edges for v in e.verts}
assert all(sum(e in hole_edges for e in v.link_edges)==2 for v in hole_verts),'Body cut is not one simple loop'
hole_positions=[v.co.copy() for v in hole_verts]
bb.to_mesh(body.data);bb.free();body.data.update()

# Save correspondence through object join using dedicated vertex groups.
root_ids=[v.index for v in ob.data.vertices if any((v.co-p).length<1e-7 for p in root_positions)]
hole_ids=[v.index for v in body.data.vertices if any((v.co-p).length<1e-7 for p in hole_positions)]
ob.vertex_groups.new(name='JOIN inner').add(root_ids,1,'REPLACE')
body.vertex_groups.new(name='JOIN outer').add(hole_ids,1,'REPLACE')
# Give the body material an explicit UV layer, independent of active source UVs.
mat=body.data.materials[0]
uvnode=mat.node_tree.nodes.new('ShaderNodeUVMap');uvnode.uv_map='Original game UV'
for node in mat.node_tree.nodes:
    if node.type=='TEX_IMAGE':mat.node_tree.links.new(uvnode.outputs['UV'],node.inputs['Vector'])
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.join();joined=body;joined.name='Kliff neutral body - connected topology prototype'
bm=bmesh.new();bm.from_mesh(joined.data);bm.verts.ensure_lookup_table()
deform=bm.verts.layers.deform.verify()
def loop(name):
    gi=joined.vertex_groups[name].index
    vs=[v for v in bm.verts if v[deform].get(gi,0)>.5]
    return sorted(vs,key=lambda v:math.atan2(v.co.z-center.z,v.co.x))
inner=loop('JOIN inner');outer=loop('JOIN outer')
assert len(inner)==128 and len(outer)>=8,(len(inner),len(outer))
def angles(vs):return [math.atan2(v.co.z-center.z,v.co.x) for v in vs]
ai=angles(inner);ao=angles(outer)
# Stitch loops of different densities without duplicating either boundary.
i=j=0;newfaces=[]
while i<len(inner) or j<len(outer):
    ni=ai[(i+1)%len(inner)]+(2*math.pi if i+1>=len(inner) else 0) if i<len(inner) else float('inf')
    nj=ao[(j+1)%len(outer)]+(2*math.pi if j+1>=len(outer) else 0) if j<len(outer) else float('inf')
    a=inner[i%len(inner)];b=outer[j%len(outer)]
    if ni<nj:f=bm.faces.new((a,b,inner[(i+1)%len(inner)]));i+=1
    else:f=bm.faces.new((a,b,outer[(j+1)%len(outer)]));j+=1
    f.material_index=0;f.smooth=True;newfaces.append(f)
    layer=bm.loops.layers.uv.get('Original game UV')
    for l in f.loops:l[layer].uv=skin_uv(l.vert.co)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
join_edges={e for v in inner+outer for e in v.link_edges if all(q in set(inner+outer) for q in e.verts)}
assert all(e.is_manifold for e in join_edges),'Join has an open or multiply shared edge'
zero=sum(f.calc_area()<1e-12 for f in bm.faces)
assert zero==0,zero
report={'stage':'Connected topology prototype; not game-ready','join_inner_vertices':len(inner),'join_outer_vertices':len(outer),'bridge_triangles':len(newfaces),'join_open_or_nonmanifold_edges':sum(not e.is_manifold for e in join_edges),'zero_area_faces':zero,'vertices':len(bm.verts),'faces':len(bm.faces),'placement_change_m':-.03,'relative_scale_to_v02':1.20,'runtime_tested':False,'remaining':['Visual review of bridge and UV transition','Transfer blended skin weights across new surface','Validate default Kliff skeleton proportions','Game texture bake, LODs and clothing visibility','Runtime physics support']}
bm.to_mesh(joined.data);bm.free();joined.data.update()
joined.data.normals_split_custom_set([(0,0,0)]*len(joined.data.loops))
convert=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
arm=bpy.data.armatures.new('Original full-body skeleton')
rig=bpy.data.objects.new('Kliff original skeleton - deformation review',arm);scene.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for b in original['bones']:
    bone=arm.edit_bones.new(b['name']);bone.matrix=convert@Matrix([b['matrix'][i:i+4] for i in range(0,16,4)]).transposed()@convert.inverted();bone.length=.035
for b in original['bones']:
    if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[original['bones'][b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT')
mod=joined.modifiers.new('Original game skeleton weights','ARMATURE');mod.object=rig
joined.parent=rig;rig.hide_set(True)
report['skinning']='Original body weights retained; nearest-triangle weights blended across attachment into original pelvis; at most six attachment influences.'
report['remaining'].remove('Transfer blended skin weights across new surface')
joined['status']=report['stage'];joined['source_attribution']='ThineCrawler, CC BY-SA 4.0; local game body reference.'
for f in joined.data.polygons:f.use_smooth=True
scene['Stage']=report['stage']
scene.cycles.samples=24
cam=scene.camera
cam.location=(1.8,3,1.2);cam.rotation_euler=(Vector((0,.05,.97))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.95
scene.render.filepath=str(OUT/'neutral-body-review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-connected-body.blend'))
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
bpy.ops.render.render(write_still=True)
print(json.dumps(report,indent=2))
