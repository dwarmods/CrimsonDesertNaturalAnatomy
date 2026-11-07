import bpy,json,heapq,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/Kliff-Body-Editor';(OUT/'web/assets').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'outputs/Kliff-Neutral-Body-v0.3-REVIEW/Kliff-neutral-body-review.blend'),load_ui=False,use_scripts=False)
body=bpy.data.objects['Kliff neutral body - connected topology prototype']
visible=[o for o in bpy.data.objects if o.type=='MESH' and o.visible_get() and not o.hide_render]
keep=set(visible)
for o in visible:
 if o.parent:keep.add(o.parent)
 for m in o.modifiers:
  if m.type=='ARMATURE' and m.object:keep.add(m.object)
for o in list(bpy.data.objects):
 if o not in keep:bpy.data.objects.remove(o,do_unlink=True)
def positions(o):
 keys=o.data.shape_keys
 if keys and 'Default Kliff - native affine preview' in keys.key_blocks:return [v.co.copy() for v in keys.key_blocks['Default Kliff - native affine preview'].data]
 return [v.co.copy() for v in o.data.vertices]
coords=positions(body)
def group_indices(name):
 gi=body.vertex_groups[name].index
 return [v.index for v in body.data.vertices if any(g.group==gi and g.weight>.5 for g in v.groups)]
inner=group_indices('JOIN inner');outer=group_indices('JOIN outer')
pivot=sum((coords[i] for i in inner),Vector())/len(inner)
# Anatomy and bridge are one connected mesh. Extend the displacement smoothly
# into the neighboring torso instead of translating a disconnected attachment.
anatomy={i for p in body.data.polygons if p.material_index==1 for i in p.vertices}
adj=[[] for _ in coords]
for e in body.data.edges:
 a,b=e.vertices;d=(coords[a]-coords[b]).length;adj[a].append((b,d));adj[b].append((a,d))
dist=[math.inf]*len(coords);queue=[]
for i in anatomy:dist[i]=0;heapq.heappush(queue,(0,i))
while queue:
 d,i=heapq.heappop(queue)
 if d!=dist[i] or d>.12:continue
 for j,c in adj[i]:
  nd=d+c
  if nd<dist[j]:dist[j]=nd;heapq.heappush(queue,(nd,j))
weights=[]
for d in dist:
 t=max(0,1-d/.10);weights.append(t*t*(3-2*t))
# Deformation is shared verbatim by the browser and Blender exporter.
rows=[]
for o in visible:
 o.data.calc_loop_triangles();p=positions(o)
 rows.append({'name':o.name,'editable':o==body,'positions':[x for v in p for x in v],
 'indices':[i for tri in o.data.loop_triangles for i in tri.vertices],
 'weights':weights if o==body else [],'region':sorted(anatomy) if o==body else [],
 'join':inner+outer if o==body else []})
asset={'schema':1,'asset':'kliff-connected-v03','up':'Z','pivot':list(pivot),'meshes':rows,
 'source_stage':'Connected body draft; texture transition and game integration unfinished'}
(OUT/'web/assets/body.json').write_text(json.dumps(asset,separators=(',',':')))
body['editor_asset']='kliff-connected-v03'
for o in bpy.data.objects:
 if o.type=='ARMATURE':o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'body-template.blend'))
print(json.dumps({'meshes':len(rows),'editable_vertices':len(coords),'region_vertices':len(anatomy),'pivot':list(pivot),'asset_bytes':(OUT/'web/assets/body.json').stat().st_size}))
