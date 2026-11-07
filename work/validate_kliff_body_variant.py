import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'neutral-body-rebuild'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Kliff-connected-body.blend'),load_ui=False,use_scripts=False)
data=json.loads((ROOT/'kliff-body-cd_phm_00_nude_01_0002.json').read_text())
base=json.loads((ROOT/'kliff-body.json').read_text())
ob=bpy.data.objects['Kliff neutral body - connected topology prototype']
rig=bpy.data.objects['Kliff original skeleton - deformation review']
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
transforms={b['name']:C@Matrix([m[i:i+4] for i in range(0,16,4)]).transposed()@C.inverted() for b,m in zip(data['bones'],data['skinning_matrices'])}
# Blender pose channels decompose matrices into location/rotation/scale and
# cannot preserve arbitrary native affine shear. Use the exact native linear
# skinning matrices as a review shape key instead of claiming a rigged match.
for pb in rig.pose.bones:pb.matrix_basis.identity()
ob.shape_key_add(name='Basis')
preview=ob.shape_key_add(name='Default Kliff - native affine preview')
group_names={g.index:g.name for g in ob.vertex_groups}
for v in ob.data.vertices:
    weights=[(group_names[g.group],g.weight) for g in v.groups if group_names[g.group] in transforms and g.weight>0]
    total=sum(w for _,w in weights)
    preview.data[v.index].co=sum((transforms[name]@v.co*(w/total) for name,w in weights),Vector()) if total else v.co
preview.value=1
for part in data['parts'][:2]:
    reference=bpy.data.objects[part['name']]
    reference.shape_key_add(name='Basis')
    shape=reference.shape_key_add(name='Default Kliff - native affine preview')
    for v,position in zip(shape.data,part['vertices']):v.co=(position[0],-position[2],position[1])
    shape.value=1
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg)
kd=KDTree(len(ob.data.vertices))
for v in ob.data.vertices:kd.insert(v.co,v.index)
kd.balance();errors=[]
for i,(old,new) in enumerate(zip(base['parts'][2]['vertices'],data['parts'][2]['vertices'])):
    p=Vector((old[0],-old[2],old[1]));co,idx,d=kd.find(p)
    # Unchanged body vertices give an independent check of rig interpretation.
    if d<1e-7:
        target=Vector((new[0],-new[2],new[1]))
        errors.append((ev.data.vertices[idx].co-target).length)
report={'variant':'Default Kliff / Character Creator body index 0','method':'Exact native affine skinning applied as a static preview shape key, not Blender pose-channel approximation','matched_unchanged_body_vertices':len(errors),'max_error_m':max(errors),'mean_error_m':sum(errors)/len(errors),'passed':max(errors)<.0005,'runtime_tested':False}
(OUT/'default-body-check.json').write_text(json.dumps(report,indent=2))
assert report['passed'],report
scene=bpy.context.scene;scene.render.filepath=str(OUT/'default-kliff-body-review.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-default-body-review.blend'))
print(json.dumps(report,indent=2))
