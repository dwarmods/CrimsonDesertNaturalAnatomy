import json,math,heapq,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor';backup=ROOT/'work/editor-before-surface-repair';backup.mkdir(exist_ok=True)
for name in ['fit.py','web/fit.js','web/app.js','export_blend.py','web/assets/body.json']:
 dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(APP/name,dest)
f=APP/'web/assets/body.json';a=json.loads(f.read_text());r=next(m for m in a['meshes'] if m['editable']);p=r['positions'];n=len(p)//3;region=set(r['region']);adj=[set() for _ in range(n)]
ix=r['indices']
for x,y,z in zip(ix[::3],ix[1::3],ix[2::3]):
 for i,j in [(x,y),(y,z),(z,x)]:adj[i].add(j);adj[j].add(i)
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def distance(seeds,limit):
 d=[math.inf]*n;q=[]
 for i in seeds:d[i]=0;heapq.heappush(q,(0,i))
 while q:
  v,i=heapq.heappop(q)
  if v!=d[i] or v>limit:continue
  for j in adj[i]:
   nd=v+math.dist(p[3*i:3*i+3],p[3*j:3*j+3])
   if nd<d[j]:d[j]=nd;heapq.heappush(q,(nd,j))
 return d
inner=[i for i in r['join'] if i in region];d=distance(inner,.065)
ids=[i for i,v in enumerate(d) if v<.065]
r['attachmentSmoothIndices']=ids;r['attachmentSmoothNeighbors']=[sorted(adj[i]) for i in ids];r['attachmentSmoothWeights']=[smooth(1-d[i]/.065) for i in ids]
# A continuous field around the entire ring, not clipped by scrotal bone weights.
r['attachmentWeights']=[smooth(1-v/.045) for v in d]
# Smooth the deformed scrotal surface, with no smoothing on the shaft or join.
ball=[min(1,r['leftWeights'][i]+r['rightWeights'][i]) for i in range(n)]
ids=[i for i,w in enumerate(ball) if w>.001]
r['scrotalSmoothIndices']=ids;r['scrotalSmoothNeighbors']=[sorted(adj[i]) for i in ids]
r['scrotalSmoothWeights']=[smooth(ball[i]/.4)*smooth(d[i]/.04) for i in ids]
f.write_text(json.dumps(a,separators=(',',':')))
# Replace weak Taubin cancellation with a bounded, convex relaxation. Every
# step averages adjacent vertices; fixed boundaries constrain the patch.
f=APP/'web/fit.js';s=(backup/'web/fit.js').read_text()
s=s.replace('if(p.attachment_smoothness)smoothAttachment', 'relaxSurface(out,.65,region.scrotalSmoothIndices,region.scrotalSmoothNeighbors,region.scrotalSmoothWeights,24);if(p.attachment_smoothness)smoothAttachment')
start=s.index('// Isotropic Taubin smoothing:')
s=s[:start]+'''// Geometry fairing of a connected patch with fixed boundaries.
export function relaxSurface(out,amount,ids,neighbors,weights,passes){
 const original=new Float64Array(out),current=new Float64Array(out),delta=new Float64Array(ids.length*3);
 for(let pass=0;pass<passes;pass++){
  for(let k=0;k<ids.length;k++)for(let a=0;a<3;a++){
   let sum=0;for(const j of neighbors[k])sum+=current[j*3+a];
   delta[k*3+a]=(sum/neighbors[k].length-current[ids[k]*3+a])*.4*weights[k];
  }
  for(let k=0;k<ids.length;k++)for(let a=0;a<3;a++)current[ids[k]*3+a]+=delta[k*3+a];
 }
 for(const i of ids)for(let a=0;a<3;a++){const j=i*3+a;out[j]=original[j]+amount*(current[j]-original[j]);}
}
export function smoothAttachment(out,amount,r){relaxSurface(out,amount,r.attachmentSmoothIndices,r.attachmentSmoothNeighbors,r.attachmentSmoothWeights,40);}
'''
f.write_text(s)
f=APP/'fit.py';s=(backup/'fit.py').read_text()
s=s.replace("    if p['attachment_smoothness']", "    relax_surface(out,.65,region['scrotalSmoothIndices'],region['scrotalSmoothNeighbors'],region['scrotalSmoothWeights'],24)\n    if p['attachment_smoothness']")
start=s.index('def smooth_attachment(')
s=s[:start]+'''def relax_surface(out,amount,ids,neighbors,weights,passes):
    original=list(out);current=list(out)
    for step in range(passes):
        delta=[[((sum(current[j*3+a] for j in neighbors[k])/len(neighbors[k]))-current[i*3+a])*.4*weights[k] for a in range(3)] for k,i in enumerate(ids)]
        for k,i in enumerate(ids):
            for a in range(3):current[i*3+a]+=delta[k][a]
    for i in ids:
        for a in range(3):
            j=i*3+a;out[j]=original[j]+amount*(current[j]-original[j])
def smooth_attachment(out,amount,r):
    relax_surface(out,amount,r['attachmentSmoothIndices'],r['attachmentSmoothNeighbors'],r['attachmentSmoothWeights'],40)
'''
f.write_text(s)
print('Rebuilt circumferential contour and attachment/scrotal smoothing fields.')
