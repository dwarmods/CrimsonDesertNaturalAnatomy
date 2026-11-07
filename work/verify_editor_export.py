import bpy,json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'outputs/Kliff-Body-Editor'))
from fit import deform
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'work/editor-test.blend'),load_ui=False,use_scripts=False)
asset=json.loads((ROOT/'outputs/Kliff-Body-Editor/web/assets/body.json').read_text());row=next(m for m in asset['meshes'] if m['editable'])
p=json.loads((ROOT/'work/editor-test-preset.json').read_text())['parameters']
body=bpy.data.objects[row['name']];expected=deform(row['positions'],row['weights'],asset['pivot'],p,row)
ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
error=max(abs(v.co[a]-expected[3*i+a]) for i,v in enumerate(ev.data.vertices) for a in range(3));assert error<2e-6
unavailable=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and not Path(bpy.path.abspath(i.filepath)).is_file()]
assert not unavailable,unavailable
report={'saved_blend_reopened':True,'maximum_preview_error_metres':error,'materials_preserved':len(body.data.materials),'vertex_groups_preserved':len(body.vertex_groups),'missing_images':unavailable,'unpacked_image_sources':[(i.name,i.source) for i in bpy.data.images if not i.packed_file],'image_count':len(bpy.data.images),'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'editor_shape_key_value':body.data.shape_keys.key_blocks['Editor fit'].value}
(ROOT/'work/editor-export-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
