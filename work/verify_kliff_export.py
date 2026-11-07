import bpy, json, sys, struct
from pathlib import Path
from mathutils import Vector
root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
report=json.loads((root/'validation.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(root/'Kliff-anatomy-fit.blend'))
original={o.name:o for o in bpy.data.objects if o.name.startswith('Kliff - ')}
assert len(original)==2
assert len(bpy.data.collections['REFERENCE - Kliff from your game'].objects)==3
expected={}
deps=bpy.context.evaluated_depsgraph_get()
for name,ob in original.items():
    ev=ob.evaluated_get(deps); me=ev.to_mesh(); positions=[ev.matrix_world @ v.co for v in me.vertices]
    expected[name]=[(min(v[a] for v in positions),max(v[a] for v in positions)) for a in range(3)]
    ev.to_mesh_clear()
data=(root/'Kliff-anatomy.glb').read_bytes()
magic,version,total=struct.unpack_from('<III',data)
assert magic==0x46546C67 and version==2 and total==len(data)
length,kind=struct.unpack_from('<II',data,12); assert kind==0x4E4F534A
gltf=json.loads(data[20:20+length])
assert len(gltf['meshes'])==2 and len(gltf['skins'])==1
assert any(node.get('name')=='Bip01 Pelvis' for node in gltf['nodes'])
for m in gltf['meshes']:
    for prim in m['primitives']:
        assert {'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}<=set(prim['attributes'])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(root/'Kliff-anatomy.glb'))
custom_shapes={pb.custom_shape for ob in bpy.context.scene.objects if ob.type=='ARMATURE' for pb in ob.pose.bones if pb.custom_shape}
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in custom_shapes]
assert len(meshes)==2,[(o.name,o.type) for o in bpy.context.scene.objects]
errors=[]
for ob in meshes:
    points=[ob.matrix_world @ v.co for v in ob.data.vertices]
    bounds=[(min(v[a] for v in points),max(v[a] for v in points)) for a in range(3)]
    assert ob.name in expected,ob.name
    error=max(abs(bounds[a][b]-expected[ob.name][a][b]) for a in range(3) for b in range(2))
    assert error<.00002,(ob.name,bounds,expected[ob.name],error)
    errors.append(error)
    assert all(abs(sum(g.weight for g in v.groups)-1)<1e-5 for v in ob.data.vertices)
report['export_verification']={'blend_reopened':True,'glb_reimported':True,'mesh_count':2,
    'skin_count':1,'reference_game_geometry_in_glb':False,'max_bounds_error_m':max(errors),
    'uvs_normals_skin_attributes_present':True,'reimported_weights_normalized':True}
(root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['export_verification'],indent=2))
