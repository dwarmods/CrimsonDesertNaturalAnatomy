import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Anatomy-Model-v0.2/Kliff-source-fit.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects['Kliff anatomy - ThineCrawler source rig'];ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
groups={g.index:g.name for g in ob.vertex_groups}
rows=[]
for v in mesh.vertices:
 weights={groups[g.group]:g.weight for g in v.groups if groups[g.group].startswith('DEF.balls')}
 rows.append({'source_world':list(ob.matrix_world@v.co),'left':weights.get('DEF.balls.L',0),'right':weights.get('DEF.balls.R',0)})
ev.to_mesh_clear()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Body-Editor/body-template.blend'),load_ui=False,use_scripts=False)
body=bpy.data.objects['Kliff neutral body - connected topology prototype'];basis=body.data.shape_keys.key_blocks['Basis'];preview=body.data.shape_keys.key_blocks['Default Kliff - native affine preview']
indices=sorted({i for p in body.data.polygons if p.material_index==1 for i in p.vertices});assert len(indices)==len(rows)
assert indices==list(range(indices[0],indices[0]+len(rows)))
old_root=Vector((0,.122,.945));new_root=Vector((0,.118,.915));errors=[]
for index,row in zip(indices,rows):
 v=Vector(row['source_world']);expected=new_root+(v-old_root)*1.2
 if (v-old_root).length>.08:errors.append((basis.data[index].co-expected).length)
 row['index']=index;row['current']=list(preview.data[index].co)
assert max(errors)<1e-5,max(errors)
def box(vs):return [[min(v[a] for v in vs),max(v[a] for v in vs)] for a in range(3)]
report={'matched_source_order_vertices':len(errors),'max_order_validation_error':max(errors),'offset':indices[0],
 'left_bounds':box([r['current'] for r in rows if r['left']>.8]),'right_bounds':box([r['current'] for r in rows if r['right']>.8]),
 'rows':rows}
(ROOT/'work/editor-anatomy-mapping.json').write_text(json.dumps(report))
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
