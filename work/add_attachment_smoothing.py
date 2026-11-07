import json,heapq,math
from pathlib import Path
APP=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor'
f=APP/'web/assets/body.json';asset=json.loads(f.read_text());r=next(m for m in asset['meshes'] if m['editable']);p=r['positions'];n=len(p)//3
adj=[set() for _ in range(n)];ix=r['indices']
for a,b,c in zip(ix[::3],ix[1::3],ix[2::3]):
 for i,j in [(a,b),(b,c),(c,a)]:adj[i].add(j);adj[j].add(i)
region=set(r['region']);q=[];d=[math.inf]*n
for i in r['join']:
 if i in region:d[i]=0;heapq.heappush(q,(0,i))
while q:
 v,i=heapq.heappop(q)
 if v!=d[i] or v>.035:continue
 for j in adj[i]:
  nd=v+math.dist(p[3*i:3*i+3],p[3*j:3*j+3])
  if nd<d[j]:d[j]=nd;heapq.heappush(q,(nd,j))
ids=[i for i,v in enumerate(d) if v<.035];r['attachmentSmoothIndices']=ids
r['attachmentSmoothNeighbors']=[sorted(adj[i]) for i in ids]
r['attachmentSmoothWeights']=[(1-d[i]/.035)**2*(1+2*d[i]/.035) for i in ids]
f.write_text(json.dumps(asset,separators=(',',':')))
f=APP/'web/fit.js';s=f.read_text().replace('attachment_contour:[-8,8,0],','attachment_contour:[-8,8,0],attachment_smoothness:[0,1,0],')
s=s.replace("'attachment_contour','shaft_base_width'", "'attachment_contour','attachment_smoothness','shaft_base_width'")
s=s.replace('return out;}', 'if(p.attachment_smoothness)smoothAttachment(out,p.attachment_smoothness,region);return out;}')
s+='''
// Isotropic Taubin smoothing: the same stencil and falloff around the full ring.
export function smoothAttachment(out,amount,r){
 const ids=r.attachmentSmoothIndices,neighbors=r.attachmentSmoothNeighbors,weights=r.attachmentSmoothWeights;
 const original=new Float64Array(out),current=new Float64Array(out),delta=new Float64Array(ids.length*3);
 for(let pass=0;pass<12;pass++){
  const coefficient=pass%2===0?.5:-.53;
  for(let k=0;k<ids.length;k++)for(let a=0;a<3;a++){
   let sum=0;for(const j of neighbors[k])sum+=current[j*3+a];
   delta[k*3+a]=(sum/neighbors[k].length-current[ids[k]*3+a])*coefficient*weights[k];
  }
  for(let k=0;k<ids.length;k++)for(let a=0;a<3;a++)current[ids[k]*3+a]+=delta[k*3+a];
 }
 for(const i of ids)for(let a=0;a<3;a++){const j=i*3+a;out[j]=original[j]+amount*(current[j]-original[j]);}
}
''';f.write_text(s)
f=APP/'fit.py';s=f.read_text().replace("'attachment_contour':(-8,8,0),", "'attachment_contour':(-8,8,0),'attachment_smoothness':(0,1,0),")
s=s.replace('    return out', "    if p['attachment_smoothness']:smooth_attachment(out,p['attachment_smoothness'],region)\n    return out")
s+='''
def smooth_attachment(out,amount,r):
    ids=r['attachmentSmoothIndices'];neighbors=r['attachmentSmoothNeighbors'];weights=r['attachmentSmoothWeights']
    original=list(out);current=list(out)
    for step in range(12):
        coefficient=.5 if step%2==0 else -.53
        delta=[[((sum(current[j*3+a] for j in neighbors[k])/len(neighbors[k]))-current[i*3+a])*coefficient*weights[k] for a in range(3)] for k,i in enumerate(ids)]
        for k,i in enumerate(ids):
            for a in range(3):current[i*3+a]+=delta[k][a]
    for i in ids:
        for a in range(3):
            j=i*3+a;out[j]=original[j]+amount*(current[j]-original[j])
''';f.write_text(s)
f=APP/'web/app.js';s=f.read_text().replace("const info={attachment_contour:", "const info={attachment_smoothness:['Attachment smoothness','%','Uniform smoothing around the entire join, with a soft boundary.'],attachment_contour:")
s=s.replace('[0,4,9].includes(index)','[0,5,10].includes(index)').replace("index===4?'ANATOMY", "index===5?'ANATOMY")
s=s.replace('1-Math.abs(params.attachment_contour)/2)', '1-Math.abs(params.attachment_contour)/2)*(1-params.attachment_smoothness)')
f.write_text(s)
f=APP/'export_blend.py';s=f.read_text().replace("1-abs(p['attachment_contour'])/2)", "1-abs(p['attachment_contour'])/2)*(1-p['attachment_smoothness'])");f.write_text(s)
print('Smoothing field vertices:',len(ids))
