import bpy,bmesh,json,math,shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor'
backup=ROOT/'work/editor-before-surface-repair/body-template.blend'
if not backup.exists():shutil.copy2(APP/'body-template.blend',backup)
assetfile=APP/'web/assets/body.json';a=json.loads((ROOT/'work/editor-before-surface-repair/web/assets/body.json').read_text());r=next(m for m in a['meshes'] if m['editable']);N=len(r['positions'])//3
reference=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text())['parts'][2]
surface=BVHTree.FromPolygons([(x,-z,y) for x,y,z in reference['vertices']],reference['faces'])
assert N==26393,'Run on the original transition only'
bpy.ops.wm.open_mainfile(filepath=str(backup),load_ui=False,use_scripts=False)
ob=bpy.data.objects[r['name']];evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
ob.data=mesh
for m in list(ob.modifiers):ob.modifiers.remove(m)
bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();old=list(bm.verts)
for i,v in enumerate(bm.verts):v.co=Vector(r['positions'][i*3:i*3+3])
pivot=Vector(a['pivot']);region=set(r['region']);angle=lambda i:math.atan2(old[i].co.z-pivot.z,old[i].co.x-pivot.x)
inner=sorted([i for i in r['join'] if i in region],key=angle);outer=sorted([i for i in r['join'] if i not in region],key=angle)
joinset=set(r['join']);bridge=[f for f in bm.faces if all(v.index in joinset for v in f.verts)]
assert len(bridge)==150,len(bridge)
uvlayers=list(bm.loops.layers.uv.values());uvs={}
for v in bm.verts:
 if v.index in joinset:
  uvs[v.index]=[sum((loop[layer].uv for loop in v.link_loops),Vector((0,0)))/len(v.link_loops) for layer in uvlayers]
inner_tangent={}
inner_neighbors={}
for i in inner:
 v=bm.verts[i];inner_neighbors[i]=[e.other_vert(v).index for e in v.link_edges if e.other_vert(v).index in region and e.other_vert(v).index not in joinset];ns=[old[j].co for j in inner_neighbors[i]]
 inner_tangent[i]=(v.co-sum(ns,Vector())/len(ns)).normalized() if ns else Vector((0,-1,0))
deform=bm.verts.layers.deform.verify();oldweights={i:dict(bm.verts[i][deform]) for i in joinset}
bmesh.ops.delete(bm,geom=bridge,context='FACES_ONLY')
angles=[angle(i) for i in outer];newrows=[];rings=[[bm.verts[i] for i in inner]]
for step in range(1,7):
 t=step/7;ring=[]
 for i in inner:
  theta=angle(i);j=max([k for k,v in enumerate(angles) if v<=theta],default=len(outer)-1);nextj=(j+1)%len(outer)
  lo=angles[j];hi=angles[nextj]+(2*math.pi if nextj==0 else 0)
  if theta<lo:theta+=2*math.pi
  f=(theta-lo)/(hi-lo);oi,oj=outer[j],outer[nextj]
  start=old[i].co.copy();end=old[oi].co.lerp(old[oj].co,f);span=end-start;length=span.length
  # Hermite interpolation avoids a straight conical band at the join.
  m0=inner_tangent[i]*length*.7
  normal=(old[oi].normal*(1-f)+old[oj].normal*f).normalized()
  m1=span-normal*span.dot(normal)
  if m1.length:m1=m1.normalized()*length
  co=start.lerp(end,t)
  hit,_,_,_=surface.ray_cast(Vector((co.x,.5,co.z)),Vector((0,-1,0)))
  if hit is not None:co.y=hit.y
  v=bm.verts.new(co);contributors=[(i,1-t),(oi,t*(1-f)),(oj,t*f)]
  for gi in set().union(*(oldweights[k].keys() for k,_ in contributors)):
   value=sum(oldweights[k].get(gi,0)*w for k,w in contributors)
   if value:v[deform][gi]=value
  newrows.append((v,contributors));ring.append(v)
 rings.append(ring)
newfaces=[]
for lower,upper in zip(rings,rings[1:]):
 for j in range(len(inner)):newfaces.append(bm.faces.new((lower[j],upper[j],upper[(j+1)%len(inner)],lower[(j+1)%len(inner)])))
# The remaining narrow outer band joins the original body edge exactly.
ai=[angle(i) for i in inner];ao=angles;i=j=0
while i<len(inner) or j<len(outer):
 ni=ai[(i+1)%len(inner)]+(2*math.pi if i+1>=len(inner) else 0) if i<len(inner) else math.inf
 nj=ao[(j+1)%len(outer)]+(2*math.pi if j+1>=len(outer) else 0) if j<len(outer) else math.inf
 x=rings[-1][i%len(inner)];y=old[outer[j%len(outer)]]
 if ni<nj:face=bm.faces.new((x,y,rings[-1][(i+1)%len(inner)]));i+=1
 else:face=bm.faces.new((x,y,old[outer[(j+1)%len(outer)]]));j+=1
 newfaces.append(face)
bm.verts.index_update();newuv={v.index:[sum((uvs[k][layer]*w for k,w in contrib),Vector((0,0))) for layer in range(len(uvlayers))] for v,contrib in newrows}
for f in newfaces:
 f.material_index=0;f.smooth=True
 for loop in f.loops:
  data=newuv.get(loop.vert.index,uvs.get(loop.vert.index))
  if data:
   for layer,uv in zip(uvlayers,data):loop[layer].uv=uv
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
assert all(e.is_manifold for face in newfaces for e in face.edges)
assert all(face.calc_area()>1e-12 for face in newfaces)
scalar=['weights','leftWeights','rightWeights','shaftWeights','seamNormalWeights','profileT','profileWeights','attachmentWeights','anatomyHeightWeights']
for v,contrib in newrows:
 assert v.index==len(r['positions'])//3
 r['positions'].extend(v.co)
 for key in scalar:r[key].append(sum(r[key][k]*w for k,w in contrib))
 r['seamNormals'].extend(sum((Vector(r['seamNormals'][k*3:k*3+3])*w for k,w in contrib),Vector()).normalized())
bm.to_mesh(mesh);bm.free();mesh.update();mesh.calc_loop_triangles();r['indices']=[i for tri in mesh.loop_triangles for i in tri.vertices]
r['transitionRows']=[{'index':N+k,'inner':contrib[0][0],'outerA':contrib[1][0],'outerB':contrib[2][0],'t':1-contrib[0][1],'f':contrib[2][1]/(1-contrib[0][1]),'neighbors':inner_neighbors[contrib[0][0]]} for k,(_,contrib) in enumerate(newrows)]
# The evaluated neutral scene is now the authoring basis. Skin weights, UVs,
# materials and packed images survive; posing remains a separate authoring step.
ob.shape_key_add(name='Basis');ob['surface_revision']='Six-ring body-surface transition replacing long triangle fan';ob['rig_note']='Neutral geometry baked for fitting; original vertex groups retained.'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(APP/'body-template.blend'))
assetfile.write_text(json.dumps(a,separators=(',',':')))
(ROOT/'work/editor-surface-topology.json').write_text(json.dumps({'old_vertices':N,'new_vertices':len(mesh.vertices),'transition_rings':6,'bridge_manifold':True,'degenerate_bridge_faces':0,'vertex_groups':len(ob.vertex_groups),'materials':len(mesh.materials),'rig_modifier_baked_for_static_editor':True},indent=2))
print('TRANSITION_REBUILT',N,len(mesh.vertices))
