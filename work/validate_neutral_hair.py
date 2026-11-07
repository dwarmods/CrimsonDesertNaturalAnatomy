"""Reopen the hair deliverable and verify geometry, inherited weights and fitting motion."""
from pathlib import Path
import bpy, json
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/Kliff-Anatomy-Hair-0.5'
BODY='Kliff neutral body - connected topology prototype'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Anatomy-Materials-0.5/Kliff-Neutral-Anatomy-Atlas.blend'),load_ui=False,use_scripts=False)
source=bpy.data.objects[BODY]
points=np.array([tuple(v.co) for v in source.data.vertices])
faces=[tuple(p.vertices) for p in source.data.polygons]
def weights(ob,vi):
 return {ob.vertex_groups[g.group].name:g.weight for g in ob.data.vertices[vi].groups}
original_weights=[weights(source,i) for i in range(len(points))]
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Kliff-Neutral-Anatomy-With-Hair.blend'),load_ui=False,use_scripts=False)
body=bpy.data.objects[BODY];hair=bpy.data.objects['Pubic hair - surface rooted neutral groom']
assert np.array_equal(points,np.array([tuple(v.co) for v in body.data.vertices]))
assert faces==[tuple(p.vertices) for p in body.data.polygons]
assert original_weights==[weights(body,i) for i in range(len(points))]
roots=json.loads((ROOT/'work/anatomy-hair-roots.json').read_text())['roots']
native={b['name'] for b in json.loads((ROOT/'work/kliff-body.json').read_text())['bones']}
allowed=native|{g.name for g in body.vertex_groups if g.name.startswith('FIT ')}
for row in roots:
 expected={k:v for k,v in weights(body,row['donor_vertex']).items() if k in allowed and v>1e-8}
 for i in range(row['start'],row['start']+row['count']):
  assert weights(hair,i)==expected
assert body.data.materials[0]==hair.data.materials[0]
atlas_images=[n.image for n in body.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
assert len(atlas_images)==5
assert all(i.packed_file is not None for i in atlas_images)
rig=next(m.object for m in hair.modifiers if m.type=='ARMATURE')
assert rig==next(m.object for m in body.modifiers if m.type=='ARMATURE')
def evaluated(ob):
 bpy.context.view_layer.update()
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
 return np.array([tuple(v.co) for v in ev.data.vertices])
neutral_body=evaluated(body);neutral_hair=evaluated(hair)
neutral_error=float(np.max(np.abs(neutral_hair-np.array([tuple(v.co) for v in hair.data.vertices]))))
assert neutral_error<2e-6
pb=rig.pose.bones['FIT anatomy root']
pb.location=pb.bone.matrix_local.to_3x3().inverted()@Vector((0,0,-.01))
db=evaluated(body)-neutral_body;dh=evaluated(hair)-neutral_hair
error=max(float(np.max(np.abs(dh[r['start']:r['start']+r['count']]-db[r['donor_vertex']]))) for r in roots)
assert error<2e-6,error
pb.location=(0,0,0);bpy.context.view_layer.update()
native_counts={}
for ob in (body,hair):
 mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers['GameAtlas'].data
 keys=set()
 for tri in mesh.loop_triangles:
  for li in tri.loops:
   keys.add((mesh.loops[li].vertex_index,tuple(round(x,8) for x in uv[li].uv),tuple(round(x,7) for x in mesh.corner_normals[li].vector)))
 native_counts[ob.name]=len(keys)
assert sum(native_counts.values())<=65535,native_counts
report=json.loads((OUT/'Hair-Validation.json').read_text())
report['reopened_file_checks']={'body_geometry_and_all_weights_unchanged':True,'every_strand_vertex_matches_root_donor_weights':True,'shared_fitting_armature_and_atlas':True,'five_atlas_images_packed_in_blend':True,'neutral_hair_max_error_m':neutral_error,'root_10mm_motion_hair_vs_donor_max_error_m':error,'native_vertex_counts_after_uv_normal_splitting':native_counts,'combined_native_vertices':sum(native_counts.values()),'within_16bit_mesh_vertex_limit':True}
(OUT/'Hair-Validation.json').write_text(json.dumps(report,indent=2))
print('HAIR_VALIDATION_PASSED '+json.dumps(report['reopened_file_checks']))
