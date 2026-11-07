"""Deterministic surface-rooted hair groom for neutral anatomical seam coverage."""
import bpy,json,math,random,collections
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent.parent;SOURCE=ROOT/'outputs/Kliff-Anatomy-Materials-0.5';OUT=ROOT/'outputs/Kliff-Anatomy-Hair-0.5';TEX=OUT/'textures';TEX.mkdir(parents=True,exist_ok=True)
asset=json.loads((ROOT/'outputs/Kliff-Body-Editor/web/assets/body.json').read_text());region=next(m for m in asset['meshes'] if m['editable'])
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'Kliff-Neutral-Anatomy-Atlas.blend'),load_ui=False,use_scripts=False)
if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
body=bpy.data.objects[region['name']];mesh=body.data;mesh.calc_loop_triangles();surface=BVHTree.FromPolygons([v.co for v in mesh.vertices],[tuple(t.vertices) for t in mesh.loop_triangles])
positions=[v.co.copy() for v in mesh.vertices]
inner=[q['inner'] for q in region['transitionRows']];center=sum((positions[i] for i in set(inner)),Vector())/len(set(inner))
mask=mesh.color_attributes['Kliff seam mask'];zones=[];candidates=[];weights=[]
for ti,tri in enumerate(mesh.loop_triangles):
 points=[positions[i] for i in tri.vertices];c=sum(points,Vector())/3;normal=tri.normal
 radius=((c.x-center.x)/.069)**2+((c.z-(center.z+.018))/.059)**2
 if radius>=1 or normal.y<.12 or c.y<center.y-.035:continue
 # Limit hair on the attached anatomy to the immediate root, retaining a natural pubic field above it.
 shaft=max(region['shaftWeights'][i] for i in tri.vertices)
 seam=sum(mask.data[i].color[0] for i in tri.vertices)/3
 if shaft>.6 and seam<.55:continue
 density=(1-radius)**.8*(.45+1.5*seam)
 if density<=0:continue
 candidates.append(ti);weights.append(tri.area*density)
assert len(candidates)>20,len(candidates)
rng=random.Random(20261030);count=1550;rings=6;sides=3
vertices=[];faces=[];uvs=[];root_records=[];native_bone_names={b['name'] for b in json.loads((ROOT/'work/kliff-body.json').read_text())['bones']}
for strand in range(count):
 tri=mesh.loop_triangles[rng.choices(candidates,weights=weights,k=1)[0]];a,b,c=[positions[i] for i in tri.vertices]
 u=rng.random();v=rng.random()
 if u+v>1:u=1-u;v=1-v
 factors=(1-u-v,u,v);point=a*factors[0]+b*factors[1]+c*factors[2]
 normal=sum((mesh.vertices[i].normal*w for i,w in zip(tri.vertices,factors)),Vector()).normalized()
 down=Vector((-point.x*3+rng.uniform(-.28,.28),0,-1));tangent=down-normal*down.dot(normal)
 if tangent.length<1e-6:tangent=normal.cross(Vector((1,0,0)))
 tangent.normalize();side=normal.cross(tangent).normalized();length=rng.uniform(.014,.028);radius=rng.uniform(.000045,.00008);phase=rng.uniform(0,2*math.pi);curl=rng.uniform(.0008,.0022)
 # Use a root donor's complete weights instead of silently dropping a blended influence.
 donor=tri.vertices[max(range(3),key=lambda j:factors[j])];groups={body.vertex_groups[g.group].name:g.weight for g in mesh.vertices[donor].groups if g.weight>1e-8 and (body.vertex_groups[g.group].name in native_bone_names or body.vertex_groups[g.group].name.startswith('FIT '))}
 assert sum(name in native_bone_names for name in groups)<=6
 base=len(vertices)
 for j in range(rings):
  t=j/(rings-1);co=point+tangent*(length*t*.78)+normal*(length*(.22*math.sin(math.pi*t)+.08*t))+side*(curl*(math.sin(2*math.pi*t+phase)-math.sin(phase))*t)
  hit,hn,fi,d=surface.find_nearest(co)
  if hit is not None and (co-hit).dot(hn)<radius*.75:co=hit+hn*(radius*.75)
  width=radius*(1-.94*t)**.7
  for k in range(sides):
   angle=2*math.pi*k/sides;vertices.append(tuple(co+normal*(math.cos(angle)*width)+side*(math.sin(angle)*width)))
   # A nondegenerate chart in a reserved empty atlas border, shared by the hair geometry.
   uvs.append(((7+14*k/(sides-1))/4096,(7+14*t)/4096))
  if j:
   for k in range(sides):
    x=base+(j-1)*sides+k;y=base+(j-1)*sides+(k+1)%sides;z=base+j*sides+k;w=base+j*sides+(k+1)%sides;faces.extend(((x,y,z),(y,w,z)))
 root_records.append({'start':base,'count':rings*sides,'donor_vertex':int(donor),'weights':groups})
hair_mesh=bpy.data.meshes.new('Pubic hair strand geometry');hair_mesh.from_pydata(vertices,[],faces);hair_mesh.update();hair=bpy.data.objects.new('Pubic hair - surface rooted neutral groom',hair_mesh);bpy.context.collection.objects.link(hair)
uv=hair_mesh.uv_layers.new(name='GameAtlas');uv.active_render=True
for poly in hair_mesh.polygons:
 poly.use_smooth=True
 for li in poly.loop_indices:uv.data[li].uv=uvs[hair_mesh.loops[li].vertex_index]
for group in body.vertex_groups:hair.vertex_groups.new(name=group.name)
by_name={g.name:g for g in hair.vertex_groups}
for row in root_records:
 ids=list(range(row['start'],row['start']+row['count']))
 for name,w in row['weights'].items():by_name[name].add(ids,w,'REPLACE')
for modifier in body.modifiers:
 if modifier.type=='ARMATURE':m=hair.modifiers.new(modifier.name,'ARMATURE');m.object=modifier.object;m.use_deform_preserve_volume=modifier.use_deform_preserve_volume
material=body.data.materials[0].copy();material.name='Connected body atlas with hair swatch';body.data.materials[0]=material;hair_mesh.materials.append(material)
swatches={'BaseColor':(.012,.006,.003,1),'Roughness':(.8,.8,.8,1),'Normal':(.5,.5,1,1),'PackedMaterial':(.67,.54,.64,1),'SkinMask':(0,0,0,1)}
texture_records=[]
for node in material.node_tree.nodes:
 if node.type!='TEX_IMAGE' or node.image is None:continue
 label=next((k for k in swatches if k.lower() in node.image.name.lower()),None)
 if label is None:continue
 image=node.image.copy();node.image=image;pixels=np.array(image.pixels[:],dtype=np.float32).reshape(4096,4096,4)
 # The body UV layout was normalized into [0.008, 0.992], leaving this 32px border unused.
 pixels[:32,:32]=swatches[label];image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(TEX/(label+'.png'));image.file_format='PNG';image.save();image.pack();texture_records.append({'name':label,'path':str(image.filepath_raw)})
hair['groom_seed']=20261030;hair['strand_count']=count;hair['purpose']='Neutral pubic seam coverage; static strand geometry with inherited body weights.'
hair['length_range_m']=[.014,.028];hair['runtime_physics']='Not implemented'
(ROOT/'work/anatomy-hair-roots.json').write_text(json.dumps({'roots':root_records,'vertices':vertices,'faces':faces,'uvs':uvs,'center':tuple(center)}))
scene=bpy.context.scene;scene.render.filepath=str(OUT/'Pubic-Hair-Review.png');scene.cycles.samples=32
bpy.ops.render.render(write_still=True)
for obj in bpy.context.selected_objects:obj.select_set(False)
rig=next((o for o in bpy.data.objects if o.type=='ARMATURE' and o.name.startswith('Anatomy fitting')),None)
if rig:rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='POSE')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-Neutral-Anatomy-With-Hair.blend'))
report={'stage':'Offline neutral surface-rooted hair groom','strand_count':count,'hair_vertices':len(vertices),'hair_triangles':len(faces),'root_distribution':'Tapered pubic field with extra density at attachment, not a uniform ring','length_range_m':[.014,.028],'radius_range_m':[.000045,.00008],'body_geometry_unchanged':True,'skin_and_authoring_weights_inherited_from_root_surface_donors':True,'maximum_native_influences':max(sum(name in native_bone_names for name in r['weights']) for r in root_records),'textures':texture_records,'game_modified':False,'in_game_tested':False,'limitations':['Strands use a small atlas swatch with the shared body material, not a validated native hair shader.','Hair has no independent runtime physics.','Coverage disguises part of the seam; attachment shape and native integration still require work.']}
(OUT/'Hair-Validation.json').write_text(json.dumps(report,indent=2));print('HAIR_GROOM_READY '+json.dumps({k:v for k,v in report.items() if k!='textures'}))
