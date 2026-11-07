"""Convert the saved neutral fit to game bind-space mesh channels, without deployment."""
from pathlib import Path
import bpy,json
from mathutils import Vector,Matrix,kdtree
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/Kliff-Anatomy-Authoring-0.4'
bind=json.loads((ROOT/'work/anatomy-native-bind-input.json').read_text());source=json.loads((ROOT/'work/kliff-body.json').read_text());variation=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text())
audit=json.loads((ROOT/'work/anatomy-palette-slot-audit.json').read_text());slot=audit['unused_slots'][0][0]
palette=list(source['palette']);pelvis=next(b['index'] for b in source['bones'] if b['name']=='Bip01 Pelvis');palette[slot]=pelvis
slot_by_name={source['bones'][bi]['name']:i for i,bi in enumerate(palette)}
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Kliff-Neutral-Anatomy-Controls.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects['Kliff neutral body - connected topology prototype'];mesh=ob.data;mesh.calc_loop_triangles();uvs=mesh.uv_layers.active.data
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
transforms={b['name']:C@Matrix([m[i:i+4] for i in range(0,16,4)]).transposed()@C.inverted() for b,m in zip(variation['bones'],variation['skinning_matrices'])}
source_points=[Vector((v[0],-v[2],v[1])) for v in source['parts'][2]['vertices']]
tree=kdtree.KDTree(len(source_points))
for i,v in enumerate(source_points):tree.insert(v,i)
tree.balance()
def native(v):return (float(v[0]),float(v[2]),float(-v[1]))
row={'name':'CD_PHM_00_Nude_0001','vertices':[],'normals':[],'uvs':[],'faces':[],'bone_indices':[],'bone_weights':[],'source_donors':[],'material_indices':[],'authoring_vertex_indices':[]};mapping={};inverse_normals={};native_weights={};donors={};maximum_donor_distance=0.
for i,v in enumerate(mesh.vertices):
 weights=bind['weights'][str(i)];total=sum(weights.values());A=Matrix(((0,0,0,0),)*4)
 for name,w in weights.items():A+=transforms[name]*(w/total)
 inverse_normals[i]=A.to_3x3().transposed()
 pairs=sorted(((slot_by_name[name],w/total) for name,w in weights.items() if w>1e-8),key=lambda x:(-x[1],x[0]))
 if not 1<=len(pairs)<=6:raise RuntimeError('Native bone influence capacity exceeded')
 native_weights[i]=pairs
 _,donor,distance=tree.find(Vector(bind['positions_blender_bind'][i]));donors[i]=donor;maximum_donor_distance=max(maximum_donor_distance,distance)
for tri in mesh.loop_triangles:
 face=[]
 for li in tri.loops:
  vi=mesh.loops[li].vertex_index;uv=tuple(uvs[li].uv);normal=(inverse_normals[vi]@mesh.corner_normals[li].vector).normalized();key=(vi,tuple(round(x,8) for x in uv),tuple(round(x,7) for x in normal))
  if key not in mapping:
   mapping[key]=len(row['vertices']);row['authoring_vertex_indices'].append(vi);row['vertices'].append(native(bind['positions_blender_bind'][vi]));row['normals'].append(native(normal));row['uvs'].append(uv)
   row['bone_indices'].append([i for i,w in native_weights[vi]]);row['bone_weights'].append([w for i,w in native_weights[vi]]);row['source_donors'].append(donors[vi])
  face.append(mapping[key])
 row['faces'].append(face);row['material_indices'].append(mesh.polygons[tri.polygon_index].material_index)
if len(row['vertices'])>65535:raise RuntimeError('PAC index capacity exceeded after UV/normal splitting')
report={'source_sha256':source['sha256'],'palette_reuse_slot':slot,'palette_replaced_bone':source['bones'][source['palette'][slot]]['name'],'palette_new_bone':'Bip01 Pelvis','row':row,'maximum_opaque_record_donor_distance_m':maximum_donor_distance,'material_limit':'Two Blender material zones currently map to one original game draw material. Shader/texture atlas integration remains unfinished.'}
(ROOT/'work/anatomy-pac-native-input.json').write_text(json.dumps(report));print(json.dumps({k:v for k,v in report.items() if k!='row'},indent=2));print('vertices',len(row['vertices']),'triangles',len(row['faces']))
