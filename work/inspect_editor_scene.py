import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(root/'outputs/Kliff-Neutral-Body-v0.3-REVIEW/Kliff-neutral-body-review.blend'),load_ui=False,use_scripts=False)
rows=[]
for o in bpy.data.objects:
 if o.type=='MESH':
  rows.append(dict(name=o.name,visible=o.visible_get(),hidden=o.hide_render,vertices=len(o.data.vertices),materials=[m.name if m else None for m in o.data.materials],shape_keys=[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],groups=[g.name for g in o.vertex_groups if 'JOIN' in g.name],bounds=[list(o.matrix_world@__import__('mathutils').Vector(c)) for c in o.bound_box]))
(root/'work/editor-scene-inspection.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
