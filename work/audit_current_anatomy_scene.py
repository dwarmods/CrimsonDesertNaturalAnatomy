"""Inspect neutral fitting authoring data; no game access or modifications."""
import bpy,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Body-Editor/body-template.blend'),load_ui=False,use_scripts=False)
report=[]
for ob in bpy.data.objects:
 if ob.type!='MESH' or (not ob.name.startswith('CD_PHM') and 'connected topology' not in ob.name):continue
 counts=collections.Counter();max_width=0;empty=0
 for v in ob.data.vertices:
  groups=[g for g in v.groups if g.weight>1e-8]
  max_width=max(max_width,len(groups));empty+=not groups
  for g in groups:counts[ob.vertex_groups[g.group].name]+=1
 report.append({'name':ob.name,'vertices':len(ob.data.vertices),'faces':len(ob.data.polygons),'materials':[m.name for m in ob.data.materials],'modifiers':[(m.name,m.type,m.show_viewport) for m in ob.modifiers],'shape_keys':[(k.name,k.value) for k in ob.data.shape_keys.key_blocks] if ob.data.shape_keys else [],'matrix_world':[list(r) for r in ob.matrix_world],'maximum_skin_influences':max_width,'unweighted_vertices':empty,'used_groups':dict(counts),'custom_properties':{k:ob[k] for k in ob.keys() if isinstance(ob[k],(str,int,float,bool))}})
(ROOT/'work/current-anatomy-scene-audit.json').write_text(json.dumps(report,indent=2))
for r in report:print(json.dumps({k:v for k,v in r.items() if k!='used_groups'},indent=2));print('extra groups',[(n,c) for n,c in r['used_groups'].items() if not n.startswith('Bip01')][:15])
