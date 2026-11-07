import bpy,json,heapq,math,bmesh
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'work/editor-v10-template.blend'),load_ui=False,use_scripts=False)
body=bpy.data.objects['Kliff neutral body - connected topology prototype'];key=body.data.shape_keys.key_blocks['Default Kliff - native affine preview']
coords=[v.co.copy() for v in key.data];original=[p.copy() for p in coords]
mapping=json.loads((ROOT/'work/editor-anatomy-mapping.json').read_text());anatomy={r['index'] for r in mapping['rows']}
left=[0.0]*len(coords);right=[0.0]*len(coords)
for r in mapping['rows']:left[r['index']]=r['left'];right[r['index']]=r['right']
def ids(name):
 gi=body.vertex_groups[name].index
 return [v.index for v in body.data.vertices if any(g.group==gi and g.weight>.5 for g in v.groups)]
inner=ids('JOIN inner');outer=ids('JOIN outer');pivot=sum((coords[i] for i in inner),Vector())/len(inner)
adj=[[] for _ in coords]
for e in body.data.edges:
 a,b=e.vertices;d=(coords[a]-coords[b]).length;adj[a].append((b,d));adj[b].append((a,d))
def distances(seeds,limit):
 dist=[math.inf]*len(coords);queue=[]
 for i in seeds:dist[i]=0;heapq.heappush(queue,(0,i))
 while queue:
  d,i=heapq.heappop(queue)
  if d!=dist[i] or d>limit:continue
  for j,c in adj[i]:
   nd=d+c
   if nd<dist[j]:dist[j]=nd;heapq.heappush(queue,(nd,j))
 return dist
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
rootdist=distances(inner,.25)
for i in anatomy:
 fade=smooth(rootdist[i]/.035);left[i]*=fade;right[i]*=fade
reference=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text())['parts'][2]
surface=BVHTree.FromPolygons([(x,-z,y) for x,y,z in reference['vertices']],reference['faces'])
refcoords=[Vector((x,-z,y)) for x,y,z in reference['vertices']];refnormals=[Vector() for _ in refcoords]
for face in reference['faces']:
 a,b,c=[refcoords[i] for i in face];n=(b-a).cross(c-a)
 for i in face:refnormals[i]+=n
for n in refnormals:n.normalize()
# Reduce the previously enlarged ring, and fit it flush to the uncut body.
for i in anatomy:
 p=coords[i];t=smooth(1-rootdist[i]/.052)
 p.x=pivot.x+(p.x-pivot.x)*(1-.36*t)
 p.z=pivot.z+(p.z-pivot.z)*(1-.20*t)
 if rootdist[i]<.018:
  hit,_,_,_=surface.ray_cast(Vector((p.x,.5,p.z)),Vector((0,-1,0)))
  if hit is not None:p.y=p.y*(1-smooth(1-rootdist[i]/.018))+hit.y*smooth(1-rootdist[i]/.018)
# The source weights isolate scrotal tissue. Lower it without lengthening the
# shaft; modest lateral volume recovery prevents a flattened side profile.
def center(weights):
 total=sum(weights);return sum((coords[i]*w for i,w in enumerate(weights)),Vector())/total
lc=center(left);rc=center(right)
for i in anatomy:
 p=coords[i];l=left[i];r=right[i];w=min(1,l+r)
 if w:
  c=(lc*l+rc*r)/(l+r)
  p.x+=(p.x-c.x)*.16*w
  p.y-=(.003)*w
  p.z-=.024*w
  p.z-=(.0025*l) # Small asymmetry in the resting shape, kept out of the rig.
for i,p in enumerate(coords):key.data[i].co=p
body.data.update();bpy.context.view_layer.update()
# Skinning and all UV/colour data remain attached to the same vertices.
bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
for i,p in enumerate(coords):bm.verts[i].co=p
join=set(inner+outer);join_edges=[e for e in bm.edges if all(v.index in join for v in e.verts)]
assert all(e.is_manifold for e in join_edges)
assert sum(f.calc_area()<1e-12 for f in bm.faces)==0
bm.free()
shaft=[0.0]*len(coords)
for i in anatomy:shaft[i]=(1-smooth((left[i]+right[i])/.35))*smooth(rootdist[i]/.028)
lc=center(left);rc=center(right)
falloff=distances(anatomy,.12);weights=[smooth(1-d/.10) for d in falloff]
seamdist=distances(inner+outer,.018);seamweights=[smooth(1-d/.018) for d in seamdist];seamnormals=[]
for i,p in enumerate(coords):
 if seamweights[i]:
  loc,n,fi,d=surface.find_nearest(p);face=reference['faces'][fi]
  bary=barycentric_transform(loc,*[refcoords[j] for j in face],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
  n=sum((refnormals[j]*bary[k] for k,j in enumerate(face)),Vector()).normalized()
 else:n=Vector((0,1,0))
 seamnormals.extend(n)
rows=[]
for o in bpy.data.objects:
 if o.type!='MESH' or not o.visible_get() or o.hide_render:continue
 o.data.calc_loop_triangles();k=o.data.shape_keys
 p=[v.co for v in k.key_blocks['Default Kliff - native affine preview'].data] if k else [v.co for v in o.data.vertices]
 row={'name':o.name,'editable':o==body,'positions':[x for v in p for x in v],'indices':[i for tri in o.data.loop_triangles for i in tri.vertices],'weights':weights if o==body else [],'region':sorted(anatomy) if o==body else [],'join':inner+outer if o==body else []}
 if o==body:row.update(shaftWeights=shaft,leftWeights=left,rightWeights=right,leftCenter=list(lc),rightCenter=list(rc),seamNormals=seamnormals,seamNormalWeights=seamweights)
 rows.append(row)
asset={'schema':1,'asset':'kliff-connected-v04','up':'Z','pivot':list(pivot),'meshes':rows,'source_stage':'Revised neutral fitting draft; texture transition and game integration unfinished'}
(APP/'web/assets/body.json').write_text(json.dumps(asset,separators=(',',':')))
body['editor_asset']=asset['asset'];body['revision']='Narrowed attachment and independently lowered scrotal tissue'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(APP/'body-template.blend'))
def width(points):return max(p.x for p in points)-min(p.x for p in points)
report={'asset':asset['asset'],'attachment_width_before_mm':width([original[i] for i in inner])*1000,'attachment_width_after_mm':width([coords[i] for i in inner])*1000,'left_weighted_drop_mm':sum(left[i]*(original[i].z-coords[i].z) for i in anatomy)/sum(left)*1000,'right_weighted_drop_mm':sum(right[i]*(original[i].z-coords[i].z) for i in anatomy)/sum(right)*1000,'join_edges_manifold':True,'topology_and_skin_weights_preserved':True}
(ROOT/'work/editor-anatomy-repair.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
