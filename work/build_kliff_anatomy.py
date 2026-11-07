"""Build an original relaxed adult anatomical attachment and a fitting scene.

Run with Blender --background --python this_file -- input.json output_directory.
Input is the locally extracted Kliff body produced by prepare_kliff.py.
The authoring coordinates are metres, Z up, +Y forward. No game files are edited.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:]
INPUT, OUT = Path(args[0]).resolve(), Path(args[1]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
body=json.loads(INPUT.read_text(encoding='utf-8'))
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
reference=bpy.data.collections.new('REFERENCE - Kliff from your game')
anatomy=bpy.data.collections.new('MODEL - original adult anatomy')
studio=bpy.data.collections.new('STUDIO - inspection only')
for c in (reference,anatomy,studio): scene.collection.children.link(c)

def material(name,color,roughness):
    mat=bpy.data.materials.new(name); mat.diffuse_color=(*color,1); mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Roughness'].default_value=roughness
    return mat

clay=material('Neutral sculpture clay',(.34,.385,.40),.68)
detail_clay=material('Anatomy clay',(.34,.385,.40),.60)

def mesh_object(name,verts,faces,collection,mat):
    me=bpy.data.meshes.new(name+' topology'); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name,me); collection.objects.link(ob); ob.data.materials.append(mat)
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    for poly in me.polygons: poly.use_smooth=True
    return ob

body_objects=[]
for p in body['parts']:
    ob=mesh_object(p['name'],[(x,-z,y) for x,y,z in p['vertices']],p['faces'],reference,clay)
    layer=ob.data.uv_layers.new(name='Original game UV')
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            uv=p['uvs'][ob.data.loops[li].vertex_index]; layer.data[li].uv=(uv[0],1-uv[1])
    ob['source_virtual_path']='character/model/1_pc/1_phm/nude/cd_phm_00_nude_00_0001.pac'
    ob['source_sha256']=body['sha256']; ob['purpose']='Unmodified fitting reference; not a finished character assembly.'
    body_objects.append(ob)
body_ob=body_objects[2]
bvh=BVHTree.FromPolygons([v.co for v in body_ob.data.vertices],[p.vertices[:] for p in body_ob.data.polygons])
def front_surface(x,z):
    hit=bvh.ray_cast(Vector((x,.5,z)),Vector((0,-1,0)))
    if hit[0] is None: raise RuntimeError('Attachment root missed Kliff body')
    return hit[0].y

# The original pelvis bind transform provides the attachment anchor. This
# minimal one-bone fitting rig deliberately does not invent game physics bones.
pelvis=next(b for b in body['bones'] if b['name']=='Bip01 Pelvis')
convert=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
bind=Matrix([pelvis['matrix'][i:i+4] for i in range(0,16,4)]).transposed()
arm=bpy.data.armatures.new('Kliff pelvis fitting anchor')
rig=bpy.data.objects.new('Kliff pelvis anchor - static attachment',arm); anatomy.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
bone=arm.edit_bones.new('Bip01 Pelvis'); bone.matrix=convert @ bind @ convert.inverted(); bone.length=.10
bpy.ops.object.mode_set(mode='OBJECT'); rig.select_set(False); rig.show_in_front=True
rig['scope']='Single original pelvis bind transform; no dynamic simulation or full character rig.'

def ring_mesh(name,rings,n=48):
    verts=[tuple(p) for ring in rings for p in ring]
    faces=[]
    for r in range(len(rings)-1):
        for j in range(n): faces.append((r*n+j,r*n+(j+1)%n,(r+1)*n+(j+1)%n,(r+1)*n+j))
    # Small recessed end caps; rings remain easy to edit and UV seams explicit.
    for r,reverse in [(0,True),(len(rings)-1,False)]:
        center=sum((Vector(p) for p in rings[r]),Vector())/n
        idx=len(verts); verts.append(tuple(center))
        for j in range(n):
            face=(idx,r*n+j,r*n+(j+1)%n)
            faces.append(tuple(reversed(face)) if reverse else face)
    ob=mesh_object(name,verts,faces,anatomy,detail_clay)
    uv=ob.data.uv_layers.new(name='Anatomy UV')
    for p in ob.data.polygons:
        js=[ob.data.loops[li].vertex_index%n for li in p.loop_indices if ob.data.loops[li].vertex_index<len(rings)*n]
        seam=0 in js and n-1 in js
        for li in p.loop_indices:
            vi=ob.data.loops[li].vertex_index
            if vi>=len(rings)*n: u,v=.5,(0 if vi==len(rings)*n else 1)
            else:
                r,j=divmod(vi,n); u=(n if seam and j==0 else j)/n; v=r/(len(rings)-1)
            uv.data[li].uv=(.04+.92*u,.04+.92*v)
    sub=ob.modifiers.new('Surface refinement - editable cage retained','SUBSURF'); sub.levels=2; sub.render_levels=2
    vg=ob.vertex_groups.new(name='Bip01 Pelvis'); vg.add(list(range(len(verts))),1.0,'REPLACE')
    am=ob.modifiers.new('Original pelvis attachment','ARMATURE'); am.object=rig
    ob.parent=rig
    ob['authoring_state']='Original mesh; relaxed adult anatomical study; not game-installed.'
    return ob

# Centerline and cross-sections in metres. The proximal collar is fitted to
# Kliff's actual front surface. Curvature and small asymmetry create a relaxed
# gravity-directed silhouette, with a restrained foreskin fold at the tip.
sections=[
    # x, y, z, horizontal radius, depth radius
    (0,.122,.945,.026,.022),
    (0,.132,.945,.022,.019),
    (0,.148,.941,.019,.018),
    (-.0002,.159,.935,.0175,.017),
    (-.0006,.165,.927,.016,.0158),
    (-.001,.169,.917,.0153,.0154),
    (-.0014,.171,.907,.0147,.015),
    (-.0017,.172,.897,.0141,.0146),
    (-.0019,.173,.887,.0137,.0144),
    (-.002,.1735,.881,.0135,.0141),
    (-.002,.1736,.878,.0130,.0136),
    (-.002,.1736,.877,.0133,.0139),
    (-.0019,.1735,.8755,.0147,.0150),
    (-.0019,.1734,.873,.0150,.0154),
    (-.0017,.1730,.869,.0143,.0149),
    (-.0015,.1725,.865,.0125,.0134),
    (-.0013,.1720,.8615,.0100,.0110),
    (-.0012,.1717,.8585,.0070,.0080),
    (-.0011,.1715,.857,.0038,.0050),
    (-.0011,.1715,.858,.0008,.0026),
    (-.0011,.1715,.8595,.0004,.0017),
]
N=48; rings=[]
for i,(x,y,z,rx,rd) in enumerate(sections):
    if i==0:
        ring=[]
        for j in range(N):
            a=2*math.pi*j/N; xx=x+rx*math.cos(a); zz=z+rd*math.sin(a)
            ring.append((xx,front_surface(xx,zz)-.0030,zz))
    else:
        if i==1: tangent=Vector((0,1,-.15)).normalized()
        elif i>=len(sections)-3: tangent=Vector((0,0,-1))
        else: tangent=Vector((0,sections[i+1][1]-sections[i-1][1],sections[i+1][2]-sections[i-1][2])).normalized()
        radial=Vector((0,-tangent.z,tangent.y))
        ring=[]
        for j in range(N):
            a=2*math.pi*j/N
            # Sub-millimetre variation; detail stays below the silhouette.
            organic=1+.009*math.sin(3*a+i*.41)+.006*math.sin(7*a-i*.23)
            if 8<=i<=12: organic+=.018*math.sin(11*a+i*.7)
            p=Vector((x,y,z))+Vector((rx*math.cos(a)*organic,0,0))+radial*(rd*math.sin(a)*organic)
            ring.append(tuple(p))
    rings.append(ring)
shaft=ring_mesh('Kliff - penis - relaxed',rings,N)
shaft['anatomy_variant']='Relaxed with partial foreskin coverage; proportions are an initial artistic choice.'
shaft['root_fit']='Proximal ring conformed to source body surface, inset 3 mm. Not welded to reference.'

# A supporting scrotal envelope is kept as its own editable object. Its upper
# portion intersects inside the source pelvis; mild asymmetry avoids two spheres.
N=64; rings=[]
for i in range(1,34):
    theta=math.pi*i/34; st,ct=math.sin(theta),math.cos(theta)
    ring=[]
    for j in range(N):
        a=2*math.pi*j/N
        pear=1-.18*ct
        x=.029*st*math.cos(a)*pear
        y=.126+.030*st*math.sin(a)*pear
        z=.907+.047*ct + .0038*math.cos(a)*st
        z+=.004*math.exp(-(x/.009)**2)*max(0,-ct)
        # Shallow median crease and fine transverse relief, not deep furrows.
        groove=math.exp(-(x/.006)**2)*max(0,math.sin(a))
        y-=.0015*groove*st
        ripple=(.00042*math.sin(theta*32+math.sin(a*4)*.8)+.00018*math.sin(theta*57+a*5))*st
        x+=ripple*math.cos(a); y+=ripple*math.sin(a)
        ring.append((x,y,z))
    rings.append(ring)
scrotum=ring_mesh('Kliff - scrotal support',rings,N)
scrotum['root_fit']='Upper envelope overlaps inside source pelvis; separate editable supporting mesh.'
assets=[shaft,scrotum]

# Validate authoring topology and the original-pelvis attachment numerically.
report={'stage':'Blender model v0.1; not a game mod','source_body_sha256':body['sha256'],
        'source_skeleton_sha256':body['skeleton_sha256'],'coordinate_system':'metres; Z up; +Y forward',
        'physics':'Not implemented. Static original-pelvis attachment only.', 'objects':[]}
for ob in assets:
    bm=bmesh.new(); bm.from_mesh(ob.data)
    bad=sum(not e.is_manifold for e in bm.edges)
    zero=sum(f.calc_area()<1e-12 for f in bm.faces)
    collapsed=sum(e.calc_length()<1e-7 for e in bm.edges)
    assert bad==0 and zero==0 and collapsed==0,(ob.name,bad,zero,collapsed)
    assert all(math.isfinite(c) for v in bm.verts for c in v.co)
    assert all(abs(sum(g.weight for g in v.groups)-1)<1e-6 for v in ob.data.vertices)
    report['objects'].append({'name':ob.name,'control_vertices':len(bm.verts),'control_faces':len(bm.faces),
                              'non_manifold_edges':bad,'zero_area_faces':zero,'collapsed_edges':collapsed,'signed_volume_m3':bm.calc_volume(signed=True),
                              'uv_layer':'Anatomy UV','attachment':'Bip01 Pelvis, 100% normalized weights'})
    assert bm.calc_volume(signed=True)>0
    bm.free()
dg=bpy.context.evaluated_depsgraph_get()
def evaluated_positions(ob):
    ev=ob.evaluated_get(dg); me=ev.to_mesh(); result=[ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear(); return result
before=evaluated_positions(shaft)
rig.pose.bones['Bip01 Pelvis'].location=(.01,0,0); bpy.context.view_layer.update()
after=evaluated_positions(shaft)
dist=[(a-b).length for a,b in zip(after,before)]
assert max(abs(d-.01) for d in dist)<2e-5
rig.pose.bones['Bip01 Pelvis'].location=(0,0,0); bpy.context.view_layer.update()
report['pelvis_translation_test']='10 mm bone translation moves every evaluated shaft vertex by 10 mm within 0.02 mm.'

# Studio and full-body inspection cameras; neutral material keeps the work an
# anatomical modeling study and makes attachment/silhouette flaws easy to see.
scene.render.engine='CYCLES'; scene.cycles.samples=40; scene.cycles.use_denoising=True
scene.render.resolution_x=1100; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
scene.world.color=(.08,.08,.08)
scene.view_settings.view_transform='AgX'
for name,loc,power,size in [('Key',(-2,3,4),430,2.5),('Fill',(3,2,2),200,2),('Rim',(0,-3,3),330,2)]:
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
    ob=bpy.data.objects.new(name,d); studio.objects.link(ob); ob.location=loc
    ob.rotation_euler=(Vector((0,0,.94))-ob.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Fit inspection camera'); cam=bpy.data.objects.new('Fit inspection camera',camera); studio.objects.link(cam); scene.camera=cam; camera.type='ORTHO'
def view(location,target,scale):
    cam.location=location; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); camera.ortho_scale=scale
def render(name,location,target,scale):
    view(location,target,scale); scene.render.filepath=str(OUT/name); bpy.ops.render.render(write_still=True)

# Export only the original attachment meshes and its pelvis anchor.
bpy.ops.object.select_all(action='DESELECT')
for ob in assets+[rig]: ob.select_set(True)
bpy.context.view_layer.objects.active=shaft
bpy.ops.wm.obj_export(filepath=str(OUT/'Kliff-anatomy.obj'),export_selected_objects=True,apply_modifiers=False,forward_axis='NEGATIVE_Y',up_axis='Z')
bpy.ops.export_scene.gltf(filepath=str(OUT/'Kliff-anatomy.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False)
report['exports']='OBJ is editable control topology. GLB is subdivided with static pelvis skin binding. Both exclude game reference geometry.'
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

render('fit-front.png',(0,3,1.00),(0,.06,.98),.70)
render('fit-three-quarter.png',(1.8,3,1.15),(0,.08,.96),.61)
# Body reference hands obscure the side, so hide only the separate hand part.
body_objects[1].hide_render=True
render('fit-side.png',(3,1.1,1.02),(0,.06,.94),.51)
body_objects[1].hide_render=False
render('fit-full-body.png',(.4,4,1.15),(0,0,.93),2.02)

# Save a useful editable viewport, cleanly separating references and authoring.
view((1.8,3,1.15),(0,.08,.96),.61)
rig.hide_set(True)
for ob in studio.objects: ob.hide_set(True)
bpy.ops.object.select_all(action='DESELECT')
shaft.select_set(True); bpy.context.view_layer.objects.active=shaft
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active; space.region_3d.view_distance=.75
            space.region_3d.view_location=(0,.10,.96)
            space.region_3d.view_rotation=cam.rotation_euler.to_quaternion()
            space.clip_start=.001; space.clip_end=100
            space.shading.type='SOLID'; space.shading.light='STUDIO'; space.shading.color_type='MATERIAL'
            space.overlay.show_floor=False; space.overlay.show_axis_x=False; space.overlay.show_axis_y=False
scene['Deliverable']='Kliff anatomical model v0.1. Original attachment meshes plus local body reference. Editor and in-game physics are separate work.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-anatomy-fit.blend'))
print(json.dumps(report,indent=2))
