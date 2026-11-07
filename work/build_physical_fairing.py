"""Build a connected metric fairing patch, crossing old bone-mask boundaries."""
import json,math,heapq
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor'
f=APP/'web/assets/body.json';a=json.loads(f.read_text());r=next(m for m in a['meshes'] if m['editable'])
p=r['positions'];n=len(p)//3;ix=r['indices'];adj=[set() for _ in range(n)];edge={};area=[0.]*n
def sub(i,j):return [p[3*i+k]-p[3*j+k] for k in range(3)]
for x,y,z in zip(ix[::3],ix[1::3],ix[2::3]):
 u=sub(y,x);v=sub(z,x);cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];twice=math.sqrt(sum(t*t for t in cross))
 for i in (x,y,z):area[i]+=twice/6
 for i,j,k in [(x,y,z),(y,z,x),(z,x,y)]:
  adj[i].add(j);adj[j].add(i);u=sub(i,k);v=sub(j,k);key=tuple(sorted((i,j)));edge[key]=edge.get(key,0)+sum(t*s for t,s in zip(u,v))/max(twice,1e-16)/2
def distances(seeds):
 d=[math.inf]*n;q=[]
 for i in seeds:d[i]=0;heapq.heappush(q,(0,i))
 while q:
  v,i=heapq.heappop(q)
  if v!=d[i] or v>.14:continue
  for j in adj[i]:
   nd=v+math.dist(p[3*i:3*i+3],p[3*j:3*j+3])
   if nd<d[j]:d[j]=nd;heapq.heappush(q,(nd,j))
 return d
def smooth(t):t=max(0,min(1,t));return t*t*t*(t*(t*6-15)+10)
region=set(r['region']);d=distances([i for i in r['join'] if i in region])
# Broad continuous patch includes both sides of the old scrotal/shaft weight boundary.
# The distal shaft and glans stay outside this repair.
mask=[smooth((.115-v)/.05) if i in region else smooth((.065-v)/.04) for i,v in enumerate(d)]
ids=[i for i,w in enumerate(mask) if w>1e-4];lookup={i:k for k,i in enumerate(ids)}
ns=[sorted(adj[i]) for i in ids]
r['metricFairing']={'ids':ids,'neighbors':ns,'localNeighbors':[[lookup.get(j,-1) for j in js] for js in ns],
 'coefficients':[[max(1e-8,edge[tuple(sorted((i,j)))]) for j in js] for i,js in zip(ids,ns)],
 'mass':[max(area[i],1e-12)/mask[i] for i in ids]}
# Geodesic fields had angular ridges where shortest paths changed direction.
# Fair only the scalar height field; boundary and core remain exact.
h=r['anatomyHeightWeights'][:]
active=[i for i in region if 0<h[i]<1]
for _ in range(160):
 new=h[:]
 for i in active:
  cs=[max(1e-8,edge[tuple(sorted((i,j)))]) for j in adj[i]];total=sum(cs)
  new[i]=h[i]*.6+.4*sum(h[j]*w for j,w in zip(adj[i],cs))/total
 h=new
r['anatomyHeightWeights']=h
f.write_text(json.dumps(a,separators=(',',':')))
print('Metric fairing patch:',len(ids),'vertices; height field:',len(active))
