import bpy,bmesh,json
from pathlib import Path
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'outputs/Kliff-Anatomy-Model-v0.2/Kliff-source-fit.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects['Kliff anatomy - ThineCrawler source rig']
dg=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(dg)
me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
boundary={v.index for e in bm.edges if e.is_boundary for v in e.verts}
components=[]
while boundary:
    todo=[boundary.pop()];group=[]
    while todo:
        idx=todo.pop();group.append(idx)
        for e in bm.verts[idx].link_edges:
            if e.is_boundary:
                other=e.other_vert(bm.verts[idx]).index
                if other in boundary:boundary.remove(other);todo.append(other)
    pts=[ob.matrix_world @ bm.verts[i].co for i in group]
    components.append(dict(count=len(group),center=[sum(v[a] for v in pts)/len(pts) for a in range(3)],bounds=[[min(v[a] for v in pts),max(v[a] for v in pts)] for a in range(3)]))
print(json.dumps(dict(verts=len(me.vertices),faces=len(me.polygons),boundary=components,attrs=[(a.name,a.data_type,a.domain) for a in me.attributes]),indent=2))
for group in bpy.data.node_groups:
    for n in group.nodes:
        if n.type in ('ATTRIBUTE','TEX_COORD','UVMAP','VECTOR_DISPLACEMENT'):
            print('MAPPING',group.name,n.name,n.type,getattr(n,'attribute_name',''),getattr(n,'uv_map',''),getattr(n,'space',''))
