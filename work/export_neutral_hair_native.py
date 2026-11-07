"""Export a neutral atlas body and rooted groom into original game bind space."""
from pathlib import Path
import bpy,json
from mathutils import Vector,Matrix,kdtree
ROOT=Path(__file__).resolve().parent.parent
source=json.loads((ROOT/'work/kliff-body.json').read_text())
variation=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text())
slot=json.loads((ROOT/'work/anatomy-palette-slot-audit.json').read_text())['unused_slots'][0][0]
palette=list(source['palette']);palette[slot]=next(b['index'] for b in source['bones'] if b['name']=='Bip01 Pelvis')
slot_by_name={source['bones'][bi]['name']:i for i,bi in enumerate(palette)}
native_names={b['name'] for b in source['bones']}
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
transforms={b['name']:C@Matrix([m[i:i+4] for i in range(0,16,4)]).transposed()@C.inverted() for b,m in zip(variation['bones'],variation['skinning_matrices'])}
tree=kdtree.KDTree(len(source['parts'][2]['vertices']))
for i,v in enumerate(source['parts'][2]['vertices']):tree.insert((v[0],-v[2],v[1]),i)
tree.balance()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Anatomy-Hair-0.5/Kliff-Neutral-Anatomy-With-Hair.blend'),load_ui=False,use_scripts=False)
row={k:[] for k in ('vertices','normals','uvs','faces','bone_indices','bone_weights','source_donors','material_indices','authoring_vertex_indices','tangents','tangent_signs')}
row['name']='CD_PHM_00_Nude_0001';objects=[];max_distance=0.;max_reapply_error=0.;fallback_tangents=0
for object_index,name in enumerate(('Kliff neutral body - connected topology prototype','Pubic hair - surface rooted neutral groom')):
 ob=bpy.data.objects[name];mesh=ob.data;mesh.calc_loop_triangles()
 if object_index==0:mesh.calc_tangents(uvmap='GameAtlas')
 uvs=mesh.uv_layers['GameAtlas'].data;mapping={};bind=[];normal_matrices=[];tangent_matrices=[];weights=[];donors=[];start=len(row['vertices']);face_start=len(row['faces'])
 for v in mesh.vertices:
  ws={ob.vertex_groups[g.group].name:g.weight for g in v.groups if ob.vertex_groups[g.group].name in native_names and g.weight>1e-8}
  total=sum(ws.values());assert total>0
  A=Matrix(((0,0,0,0),)*4)
  for bone,w in ws.items():A+=transforms[bone]*(w/total)
  assert abs(A.to_3x3().determinant())>1e-8
  inverse=A.inverted();co=inverse@v.co;bind.append(co);normal_matrices.append(A.to_3x3().transposed());tangent_matrices.append(inverse.to_3x3())
  max_reapply_error=max(max_reapply_error,(A@co-v.co).length)
  pairs=sorted(((slot_by_name[n],w/total) for n,w in ws.items()),key=lambda p:(-p[1],p[0]));assert 1<=len(pairs)<=6
  weights.append(pairs);_,donor,distance=tree.find(co);donors.append(donor);max_distance=max(max_distance,distance)
 def native(v):return (float(v[0]),float(v[2]),float(-v[1]))
 for tri in mesh.loop_triangles:
  face=[]
  for li in tri.loops:
   vi=mesh.loops[li].vertex_index;uv=(float(uvs[li].uv.x),1-float(uvs[li].uv.y));n=(normal_matrices[vi]@mesh.corner_normals[li].vector).normalized()
   if object_index==0:
    t=tangent_matrices[vi]@mesh.loops[li].tangent;t=(t-n*t.dot(n)).normalized();sign=-mesh.loops[li].bitangent_sign
   else:
    # Flat hair normal swatch has no tangent detail; use a stable orthogonal frame.
    axis=Vector((0,0,1)) if abs(n.z)<.9 else Vector((1,0,0));t=axis.cross(n).normalized();sign=1.
   if t.length<.5:
    axis=Vector((0,0,1)) if abs(n.z)<.9 else Vector((1,0,0));t=axis.cross(n).normalized();fallback_tangents+=1
   key=(vi,tuple(round(x,8) for x in uv),tuple(round(x,7) for x in n),tuple(round(x,5) for x in t),sign)
   if key not in mapping:
    mapping[key]=len(row['vertices']);row['vertices'].append(native(bind[vi]));row['normals'].append(native(n));row['uvs'].append(uv)
    row['tangents'].append(native(t));row['tangent_signs'].append(float(sign));row['bone_indices'].append([i for i,w in weights[vi]]);row['bone_weights'].append([w for i,w in weights[vi]])
    row['source_donors'].append(donors[vi]);row['authoring_vertex_indices'].append([object_index,vi])
   face.append(mapping[key])
  row['faces'].append(face);row['material_indices'].append(0)
 objects.append({'name':name,'native_vertices':len(row['vertices'])-start,'triangles':len(row['faces'])-face_start})
assert len(row['vertices'])<=65535,len(row['vertices'])
assert max_reapply_error<2e-6
report={'source_sha256':source['sha256'],'palette_reuse_slot':slot,'row':row,'objects':objects,'UV_conversion':'Blender V-up to native V-down: V=1-V, tangent handedness reversed, normal DDS green reversed.','fallback_tangent_corners':fallback_tangents,'maximum_opaque_record_donor_distance_m':max_distance,'native_bind_roundtrip_max_error_m':max_reapply_error,'material_limit':'One common GameAtlas; native DDS and body-only material sidecar are built separately. Shader behavior remains unverified.'}
(ROOT/'work/anatomy-hair-native-input.json').write_text(json.dumps(report))
print('NATIVE_HAIR_EXPORT '+json.dumps({k:v for k,v in report.items() if k!='row'}))
