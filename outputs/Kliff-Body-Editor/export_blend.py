import bpy,json,sys
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from fit import validate,deform,fair_normals
args=sys.argv[sys.argv.index('--')+1:];job=Path(args[0]);preset=json.loads(job.read_text());p=validate(preset['parameters'])
asset=json.loads((ROOT/'web/assets/body.json').read_text());row=next(m for m in asset['meshes'] if m['editable'])
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'body-template.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects[row['name']];basis=ob.data.shape_keys.key_blocks['Basis']
fitted=deform(row['positions'],row['weights'],asset['pivot'],p,row)
base_normals=[v.normal.copy() for v in ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
key=ob.shape_key_add(name='Editor fit');key.relative_key=basis
for i,v in enumerate(key.data):
    v.co=basis.data[i].co
    for a in range(3):v.co[a]+=fitted[3*i+a]-row['positions'][3*i+a]
key.value=1;ob['editor_preset']=json.dumps(preset);ob['editor_note']='Static fitting study; game integration and runtime physics remain unverified.'
bpy.context.view_layer.update()
# Verify the evaluated saved shape matches the interactive preview math.
evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
error=max(abs(v.co[a]-fitted[3*i+a]) for i,v in enumerate(evaluated.data.vertices) for a in range(3))
assert error<2e-6,error
# Match the editor's normal transition across the stitched attachment.
normals=[]
for i,v in enumerate(evaluated.data.vertices):
    n=v.normal.copy();w=row['seamNormalWeights'][i]
    if w:n=n.lerp(Vector(row['seamNormals'][3*i:3*i+3])+n-base_normals[i],w).normalized()
    normals.append(tuple(n))
flat=fair_normals([a for n in normals for a in n],row)
ob.data.normals_split_custom_set_from_vertices([flat[i:i+3] for i in range(0,len(flat),3)])
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='SOLID'
bpy.ops.wm.save_as_mainfile(filepath=str(job.with_suffix('.blend')))
job.with_suffix('.report.json').write_text(json.dumps({'preview_export_max_error_metres':error,'vertex_count':len(ob.data.vertices),'parameters':p,'runtime_tested':False},indent=2))
print('EDITOR_EXPORT_OK',error)
