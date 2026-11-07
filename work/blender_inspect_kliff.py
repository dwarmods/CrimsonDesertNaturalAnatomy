import bpy, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
body=json.loads((ROOT/'kliff-body.json').read_text())
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
mat=bpy.data.materials.new('Reference clay'); mat.diffuse_color=(.37,.40,.43,1)
mat.use_nodes=True
mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.37,.40,.43,1)
mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.75
for p in body['parts']:
    mesh=bpy.data.meshes.new(p['name']); mesh.from_pydata([(x,-z,y) for x,y,z in p['vertices']],[],p['faces']); mesh.update()
    ob=bpy.data.objects.new(p['name'],mesh); bpy.context.collection.objects.link(ob); ob.data.materials.append(mat)
    for f in mesh.polygons: f.use_smooth=True
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=24
scene.render.resolution_x=900; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.world.color=(.16,.16,.16)
for name,loc,power,size in [('Key',(-2,3,4),350,3),('Fill',(3,2,2),180,2),('Rim',(0,-3,3),250,2)]:
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
    ob=bpy.data.objects.new(name,d); scene.collection.objects.link(ob); ob.location=loc
    ob.rotation_euler=(Vector((0,0,.95))-ob.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Inspection camera'); cam=bpy.data.objects.new('Inspection camera',camera); scene.collection.objects.link(cam); scene.camera=cam
camera.type='ORTHO'
for name,location,target,scale in [('body',(0,4,1),(0,0,.92),2.0),('pelvis',(0,3,.95),(0,0,.94),.52),('side',(3,0,.95),(0,0,.94),.52)]:
    cam.location=location; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); camera.ortho_scale=scale
    scene.render.filepath=str(ROOT/('kliff-reference-'+name+'.png')); bpy.ops.render.render(write_still=True)
