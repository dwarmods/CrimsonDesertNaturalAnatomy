import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Anatomy-Authoring-0.4/Kliff-Neutral-Anatomy-Controls.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects['Kliff neutral body - connected topology prototype'];report={'uv_layers':[u.name for u in ob.data.uv_layers],'materials':[]}
for material in ob.data.materials:
 nodes=[]
 for n in material.node_tree.nodes:
  row={'name':n.name,'type':n.type,'inputs':[{ 'name':s.name,'linked':s.is_linked,'value':str(getattr(s,'default_value',''))[:120]} for s in n.inputs]}
  if n.type=='GROUP':row['outputs']=[s.name for s in n.outputs];row['group_name']=n.node_tree.name
  if n.type=='TEX_IMAGE':row['image']=n.image.name if n.image else None
  nodes.append(row)
 report['materials'].append({'name':material.name,'nodes':nodes,'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in material.node_tree.links]})
(ROOT/'work/current-anatomy-materials.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
