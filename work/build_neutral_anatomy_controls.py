"""Build a neutral anatomical fitting rig; original game bone weights stay separate."""
from pathlib import Path
import bpy,json,sys,math,collections
import numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor'
OUT=ROOT/'outputs/Kliff-Anatomy-Authoring-0.4';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(APP));from fit import deform
preset_path=APP/'exports/Kliff-fit-20261024-220528-84ff4e.json'
preset=json.loads(preset_path.read_text());asset=json.loads((APP/'web/assets/body.json').read_text());row=next(m for m in asset['meshes'] if m['editable'])
points=np.array(deform(row['positions'],row['weights'],asset['pivot'],preset['parameters'],row)).reshape(-1,3)
source=json.loads((ROOT/'work/kliff-body.json').read_text());variant=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(APP/'body-template.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects[row['name']]
for other in list(bpy.data.objects):
 if other.type=='ARMATURE' or (other.type=='MESH' and other!=ob and not other.name.startswith('CD_PHM')):bpy.data.objects.remove(other,do_unlink=True)
ob.shape_key_clear()
for i,v in enumerate(ob.data.vertices):v.co=points[i]
ob.data.update();original_game_weights={v.index:{ob.vertex_groups[g.group].name:g.weight for g in v.groups if ob.vertex_groups[g.group].name in {b['name'] for b in source['bones']}} for v in ob.data.vertices}

shaft=np.array(row['shaftWeights']);profile=np.array(row['profileT']);profile_weight=np.array(row['profileWeights'])
stations=[]
for lo,hi in [(0,.1),(.3,.4),(.6,.7),(.9,1.01)]:
 mask=(shaft>.8)&(profile_weight>.5)&(profile>=lo)&(profile<hi)
 if not mask.any():raise RuntimeError('Missing neutral shaft control station')
 stations.append(Vector(points[mask].mean(axis=0)))
centers=[Vector(np.average(points,axis=0,weights=np.array(row[k]))) for k in ('leftWeights','rightWeights')]
rig_data=bpy.data.armatures.new('Anatomy fitting controls');rig=bpy.data.objects.new('Anatomy fitting controls - authoring only',rig_data);bpy.context.collection.objects.link(rig)
rig.show_in_front=True;rig_data.display_type='OCTAHEDRAL';bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
def bone(name,head,tail,parent=None,connected=False):
 b=rig_data.edit_bones.new(name);b.head=head;b.tail=tail
 if parent:b.parent=rig_data.edit_bones[parent];b.use_connect=connected
 return b
anchor='FIT pelvis anchor';root='FIT anatomy root';chain=['FIT shaft base','FIT shaft middle','FIT shaft distal'];sides=['FIT scrotum left','FIT scrotum right']
bone(anchor,(0,0,.94),(0,0,1.02));bone(root,stations[0],stations[0]+Vector((0,0,.035)),anchor)
for i,name in enumerate(chain):bone(name,stations[i],stations[i+1],root if i==0 else chain[i-1],i>0)
for name,center in zip(sides,centers):bone(name,stations[0].lerp(center,.4),center,root)
bpy.ops.object.mode_set(mode='OBJECT')
rig.pose.bones[anchor].lock_location=(True,)*3;rig.pose.bones[anchor].lock_rotation=(True,)*3;rig.pose.bones[anchor].lock_scale=(True,)*3
for name in [root,*chain,*sides]:rig.pose.bones[name].rotation_mode='XYZ';rig.pose.bones[name].color.palette='THEME03'
rig['purpose']='Neutral fitting/placement controls. These are not installed game bones or runtime physics.'
rig['native_export_rule']='Bake authored fit, then recover native bind coordinates using original game weights. FIT groups never become game palette slots automatically.'
groups={name:ob.vertex_groups.new(name=name) for name in [anchor,root,*chain,*sides]}
root_mask=np.clip(np.array(row['anatomyHeightWeights']),0,1);left=np.array(row['leftWeights']);right=np.array(row['rightWeights'])
for i in range(len(points)):
 # Anchor weights explicitly retain the unmoved portion of the transition.
 h=float(root_mask[i]);s,l,r=max(0,float(shaft[i])),max(0,float(left[i])),max(0,float(right[i]));total=max(1.,s+l+r);s/=total;l/=total;r/=total
 weights={anchor:1-h,root:h*(1-s-l-r),sides[0]:h*l,sides[1]:h*r}
 t=float(profile[i]);station=t*2
 if station<=1:fractions=(1-station,station,0.)
 else:fractions=(0.,2-station,station-1)
 for name,w in zip(chain,fractions):weights[name]=h*s*max(0,w)
 for name,w in weights.items():
  if w>1e-8:groups[name].add([i],w,'REPLACE')
modifier=ob.modifiers.new('Neutral anatomical fitting controls','ARMATURE');modifier.object=rig;modifier.use_deform_preserve_volume=True

def evaluated():
 bpy.context.view_layer.update();ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());return np.array([tuple(v.co) for v in ev.data.vertices])
neutral=evaluated();neutral_error=float(np.max(np.abs(neutral-points)))
assert neutral_error<1e-6,neutral_error
rim=[i for i in row['join'] if root_mask[i]==0];torso=np.flatnonzero(root_mask==0)
pb=rig.pose.bones[root];wanted=Vector((0,0,-.01));pb.location=pb.bone.matrix_local.to_3x3().inverted()@wanted
shifted=evaluated();core=np.flatnonzero(root_mask>.999999)
core_error=float(np.max(np.abs((shifted-neutral)[core]-np.array(wanted))))
torso_error=float(np.max(np.abs(shifted[torso]-neutral[torso])))
assert core_error<2e-6 and torso_error<2e-6,(core_error,torso_error)
pb.location=(0,0,0)
rig.pose.bones[chain[1]].rotation_euler.x=math.radians(8);bent=evaluated()
shaft_motion=float(np.max(np.linalg.norm((bent-neutral)[shaft>.9],axis=1)))
assert shaft_motion>.001
assert float(np.max(np.abs(bent[torso]-neutral[torso])))<2e-6
rig.pose.bones[chain[1]].rotation_euler=(0,0,0)
pb=rig.pose.bones[sides[0]];pb.location=pb.bone.matrix_local.to_3x3().inverted()@Vector((0,0,-.008));scrotal=evaluated()
scrotal_motion=float(np.max(np.linalg.norm(scrotal-neutral,axis=1)));assert scrotal_motion>.0001
pb.location=(0,0,0);evaluated()
for v in ob.data.vertices:
 current={ob.vertex_groups[g.group].name:g.weight for g in v.groups if ob.vertex_groups[g.group].name in original_game_weights[v.index]}
 assert current==original_game_weights[v.index]

# Recover the original skeleton bind coordinates, rather than exporting the already morphed preview.
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
transforms={b['name']:C@Matrix([m[i:i+4] for i in range(0,16,4)]).transposed()@C.inverted() for b,m in zip(variant['bones'],variant['skinning_matrices'])}
bind=[];max_reapply_error=0.;minimum_determinant=float('inf')
palette_names={source['bones'][i]['name'] for i in source['palette']};missing=collections.Counter()
for i,p in enumerate(points):
 weights=original_game_weights[i];total=sum(weights.values())
 if total<=0:raise RuntimeError('Missing native game skin weights')
 A=Matrix(((0,0,0,0),)*4)
 for name,w in weights.items():
  A+=transforms[name]*(w/total)
  if name not in palette_names:missing[name]+=1
 determinant=A.to_3x3().determinant();minimum_determinant=min(minimum_determinant,abs(determinant))
 if abs(determinant)<1e-8:raise RuntimeError('Native inverse deformation is singular')
 co=A.inverted()@Vector(p);again=A@co;max_reapply_error=max(max_reapply_error,(again-Vector(p)).length);bind.append(tuple(co))
assert max_reapply_error<2e-6
bind_payload={'source_pac_sha256':source['sha256'],'variation':variant['variation'],'positions_blender_bind':bind,'faces':[list(p.vertices) for p in ob.data.polygons],'weights':original_game_weights,'missing_native_palette_bones':dict(missing),'maximum_reapply_error_m':max_reapply_error,'note':'Authoring-stage intermediate; not a valid game PAC or runtime skeleton extension.'}
(ROOT/'work/anatomy-native-bind-input.json').write_text(json.dumps(bind_payload))

ob['preset_source']=preset_path.name;ob['native_skin_groups_preserved']=True
for obj in bpy.context.selected_objects:obj.select_set(False)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='POSE');rig.data.bones.active=rig.data.bones[root]
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='SOLID';area.spaces.active.overlay.show_relationship_lines=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Kliff-Neutral-Anatomy-Controls.blend'))
(OUT/'Saved-Fit.json').write_text(json.dumps(preset,indent=2))
report={'stage':'Blender authoring controls and native bind-space conversion; game integration unfinished','control_bones':[anchor,root,*chain,*sides],'tests':{'neutral_geometry_max_error_m':neutral_error,'whole_anatomy_10mm_translation_core_max_error_m':core_error,'torso_max_displacement_m':torso_error,'shaft_8degree_test_max_displacement_m':shaft_motion,'scrotal_8mm_control_test_max_displacement_m':scrotal_motion,'original_game_weights_unchanged':True,'native_bind_roundtrip_max_error_m':max_reapply_error,'minimum_native_blend_determinant':minimum_determinant},'saved_fit':preset,'native_export_blocker':{'bones_used_but_absent_from_original_PAC_palette':dict(missing),'note':'These are existing skeleton bones, not the new FIT controls. The original palette needs a verified extension or compatible binding plan before game PAC export.'},'game_modified':False,'runtime_physics_implemented':False,'in_game_tested':False}
(OUT/'Validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='saved_fit'},indent=2))
