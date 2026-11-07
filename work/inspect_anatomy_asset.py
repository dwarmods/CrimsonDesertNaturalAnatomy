import bpy, json, sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
src, dest = (Path(p).resolve() for p in args[:2])
bpy.ops.wm.open_mainfile(filepath=str(src), load_ui=False, use_scripts=False)

def bbox(ob):
    pts = [ob.matrix_world @ Vector(v) for v in ob.bound_box]
    return [[min(v[a] for v in pts), max(v[a] for v in pts)] for a in range(3)]

objects=[]
for ob in bpy.data.objects:
    entry=dict(name=ob.name,type=ob.type,location=list(ob.location),scale=list(ob.scale),
               rotation=list(ob.rotation_euler),parent=ob.parent.name if ob.parent else None,
               hidden_render=ob.hide_render,hidden_viewport=ob.hide_viewport,bbox=bbox(ob),
               modifiers=[dict(name=m.name,type=m.type,show_viewport=m.show_viewport,show_render=m.show_render,
                               object=getattr(getattr(m,'object',None),'name',None),
                               levels=getattr(m,'levels',None),render_levels=getattr(m,'render_levels',None)) for m in ob.modifiers])
    if ob.type=='MESH':
        entry.update(vertices=len(ob.data.vertices),faces=len(ob.data.polygons),
                     uv_layers=[u.name for u in ob.data.uv_layers],
                     materials=[m.name if m else None for m in ob.data.materials],
                     shape_keys=[k.name for k in ob.data.shape_keys.key_blocks] if ob.data.shape_keys else [])
    if ob.type=='ARMATURE':
        entry['bones']=[dict(name=b.name,head=list(b.head_local),tail=list(b.tail_local),deform=b.use_deform) for b in ob.data.bones]
        entry['pose']=[dict(name=b.name,location=list(b.location),scale=list(b.scale),rotation=list(b.rotation_quaternion),
                           constraints=[dict(name=c.name,type=c.type) for c in b.constraints],
                           properties={k:str(b[k]) for k in b.keys() if k!='_RNA_UI'}) for b in ob.pose.bones]
    objects.append(entry)
drivers=[]
for seq in (bpy.data.objects,bpy.data.shape_keys,bpy.data.materials,bpy.data.node_groups):
    for block in seq:
        anim=getattr(block,'animation_data',None)
        if anim:
            for fc in anim.drivers:
                drivers.append(dict(owner=block.name,path=fc.data_path,expression=fc.driver.expression,
                                    variables=[dict(name=v.name,type=v.type) for v in fc.driver.variables]))
report=dict(source=str(src),blender=bpy.app.version_string,objects=objects,drivers=drivers,
    images=[dict(name=i.name,filepath=i.filepath,packed=bool(i.packed_file),size=list(i.size),colorspace=i.colorspace_settings.name) for i in bpy.data.images],
    embedded_texts=[dict(name=t.name,use_module=t.use_module,length=len(t.as_string())) for t in bpy.data.texts],
    materials=[dict(name=m.name,nodes=[dict(name=n.name,type=n.bl_idname,image=getattr(getattr(n,'image',None),'name',None)) for n in m.node_tree.nodes] if m.use_nodes else []) for m in bpy.data.materials])
dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('source','blender','embedded_texts')},indent=2))
for o in objects: print(o['name'],o['type'],o.get('vertices'),o['bbox'],o['parent'])
print('Images:',len(report['images']),'drivers:',len(drivers))
