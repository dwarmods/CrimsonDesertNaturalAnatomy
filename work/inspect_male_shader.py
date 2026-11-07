import bpy, sys, json
from pathlib import Path
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'source-assets/Ultimate_Realistic_Penis.blend'),load_ui=False,use_scripts=False)
mat=bpy.data.materials['Realistic Penis Shader']
for n in mat.node_tree.nodes:
    print('MATERIAL',n.name,n.type)
    if n.type=='GROUP':
        print('INPUTS',[(s.name,str(getattr(s,'default_value','')),s.is_linked) for s in n.inputs])
        print('OUTPUTS',[s.name for s in n.outputs])
        for child in n.node_tree.nodes:
            print('NODE',child.name,child.type,[(s.name,str(getattr(s,'default_value',''))) for s in child.inputs if not s.is_linked])
        for l in n.node_tree.links: print('LINK',l.from_node.name,l.from_socket.name,'>',l.to_node.name,l.to_socket.name)
ob=bpy.data.objects['Penis Main Mesh']
print('ACTIVE_UV',ob.data.uv_layers.active.name)
print('V_GROUPS',[g.name for g in ob.vertex_groups])
print('GROUPS',list(bpy.data.node_groups.keys()))
