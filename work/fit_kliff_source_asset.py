"""Fit the licensed source asset to a local Kliff body reference; no game writes."""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Matrix, Vector
ROOT=Path(__file__).resolve().parent
OUT=(ROOT.parent/'outputs/Kliff-Anatomy-Model-v0.2').resolve()
OUT.mkdir(exist_ok=True,parents=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source-assets/Ultimate_Realistic_Penis.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
rig=bpy.data.objects['Armature']
main=bpy.data.objects['Penis Main Mesh']
source_objects=list(bpy.data.objects)
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
    print('BONE',pb.name,'PARENT',pb.parent.name if pb.parent else None)
bpy.context.view_layer.update()
# Bend the shaft through its author-provided swing control. Scrotal controls
# retain their neutral transforms. This is a static fitting pose, not physics.
swing=rig.pose.bones['penis swing']
pivot=swing.head.copy()
swing.matrix=Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(67),4,'X') @ Matrix.Translation(-pivot) @ swing.matrix
bpy.context.view_layer.update()
root_point=rig.data.bones['penis_root'].head_local.copy()
fit=bpy.data.objects.new('Kliff fit transform',None)
scene.collection.objects.link(fit)
for ob in source_objects:
    if ob.parent is None:
        previous=ob.matrix_world.copy();ob.parent=fit;ob.matrix_world=previous
    if ob.type=='MESH' and ob!=main:
        ob.hide_render=True
        ob.hide_set(True)
fit.matrix_world=Matrix.Translation((0,.122,.945)) @ Matrix.Rotation(math.pi,4,'Z') @ Matrix.Scale(.72,4) @ Matrix.Translation(-root_point)
main.name='Kliff anatomy - ThineCrawler source rig'
main['source_author']='ThineCrawler'
main['source_url']='https://smutba.se/project/8f757313-b08c-41b2-a61f-2105a31d4428/'
main['license']='CC BY-SA 4.0'
main['modifications']='Neutralized pose; 0.72 scale; 67-degree relaxed shaft bend; fitted to local Kliff reference.'
rig.name='ThineCrawler authoring rig - not game physics'

reference=bpy.data.collections.new('REFERENCE - local Kliff body')
studio=bpy.data.collections.new('STUDIO - inspection')
scene.collection.children.link(reference);scene.collection.children.link(studio)
body=json.loads((ROOT/'kliff-body.json').read_text())
body_objects=[]
for i,p in enumerate(body['parts']):
    me=bpy.data.meshes.new(p['name']);me.from_pydata([(x,-z,y) for x,y,z in p['vertices']],[],p['faces']);me.update()
    ob=bpy.data.objects.new(p['name'],me);reference.objects.link(ob);body_objects.append(ob)
    for f in me.polygons:f.use_smooth=True
    uv=me.uv_layers.new(name='Original game UV')
    for loop in me.loops:
        u,v=p['uvs'][loop.vertex_index];uv.data[loop.index].uv=(u,1-v)
    texnames=['cd_phm_00_head_00_0001_01','cd_phm_00_nude_00_0001_hand','cd_phm_00_nude_00_0001']
    mat=bpy.data.materials.new('Kliff skin reference '+str(i));mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.64
    shader.inputs['Subsurface Weight'].default_value=.06
    im=bpy.data.images.load(str(ROOT/'kliff-skin'/f'{texnames[i]}.png'),check_existing=True);im.pack()
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=im
    mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color']);me.materials.append(mat)
    ob['source_sha256']=body['sha256'];ob['purpose']='Local fitting reference; original game body topology.'

# Neutral studio lighting avoids the source scene's environment dependency.
scene.world=bpy.data.worlds.new('Neutral inspection world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.055,.065,.08,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
for name,loc,power,size in [('Key',(-2,3,4),500,2.5),('Fill',(3,2,2),230,2),('Rim',(0,-3,3),350,2)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);studio.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,0,.94))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Fit camera');cam=bpy.data.objects.new('Fit camera',data);studio.objects.link(cam);scene.camera=cam;data.type='ORTHO'
def view(loc,target,scale):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
def render(name,loc,target,scale):
    view(loc,target,scale);scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)
view((1.8,3,1.15),(0,.08,.96),.61)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-source-fit.blend'))
render('fit-three-quarter.png',(1.8,3,1.15),(0,.08,.96),.61)
body_objects[1].hide_render=True
render('fit-side.png',(3,1.1,1.02),(0,.06,.94),.51)
body_objects[1].hide_render=False
render('fit-front.png',(0,3,1.00),(0,.06,.98),.70)
view((1.8,3,1.15),(0,.08,.96),.61)
for ob in studio.objects:ob.hide_set(True)
rig.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');main.select_set(True);bpy.context.view_layer.objects.active=main
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active;s.region_3d.view_distance=.75;s.region_3d.view_location=(0,.1,.96)
            s.region_3d.view_rotation=cam.rotation_euler.to_quaternion();s.clip_start=.001
            s.shading.type='MATERIAL';s.overlay.show_floor=False
scene['Stage']='Licensed anatomy source fitted to Kliff. Seam, game export and physics still require work.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-source-fit.blend'))
