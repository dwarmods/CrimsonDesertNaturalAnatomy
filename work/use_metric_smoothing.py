import json,math
from pathlib import Path
APP=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor';f=APP/'web/assets/body.json';a=json.loads(f.read_text());r=next(m for m in a['meshes'] if m['editable']);p=r['positions'];ix=r['indices'];edge={}
def sub(i,j):return [p[3*i+k]-p[3*j+k] for k in range(3)]
for x,y,z in zip(ix[::3],ix[1::3],ix[2::3]):
 for i,j,k in [(x,y,z),(y,z,x),(z,x,y)]:
  u=sub(i,k);v=sub(j,k);dot=sum(a*b for a,b in zip(u,v));cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
  cot=dot/max(1e-16,math.sqrt(sum(c*c for c in cross)));key=tuple(sorted((i,j)));edge[key]=edge.get(key,0)+cot
for prefix in ['attachment','scrotal']:
 ids=r[prefix+'SmoothIndices'];neighbors=r[prefix+'SmoothNeighbors'];coeff=[]
 for i,ns in zip(ids,neighbors):
  ws=[max(1e-6,edge[tuple(sorted((i,j)))]) for j in ns];total=sum(ws);coeff.append([w/total for w in ws])
 r[prefix+'SmoothCoefficients']=coeff
f.write_text(json.dumps(a,separators=(',',':')))
f=APP/'web/fit.js';s=f.read_text().replace('region.scrotalSmoothWeights,24','region.scrotalSmoothWeights,48,region.scrotalSmoothCoefficients')
s=s.replace('weights,passes){','weights,passes,coefficients){').replace('for(const j of neighbors[k])sum+=current[j*3+a];', 'for(let q=0;q<neighbors[k].length;q++)sum+=current[neighbors[k][q]*3+a]*coefficients[k][q];').replace('sum/neighbors[k].length-current','sum-current').replace('r.attachmentSmoothWeights,40','r.attachmentSmoothWeights,100,r.attachmentSmoothCoefficients');f.write_text(s)
f=APP/'fit.py';s=f.read_text().replace("region['scrotalSmoothWeights'],24", "region['scrotalSmoothWeights'],48,region['scrotalSmoothCoefficients']")
s=s.replace('weights,passes):','weights,passes,coefficients):').replace('sum(current[j*3+a] for j in neighbors[k])/len(neighbors[k])', 'sum(current[j*3+a]*coefficients[k][q] for q,j in enumerate(neighbors[k]))').replace("r['attachmentSmoothWeights'],40", "r['attachmentSmoothWeights'],100,r['attachmentSmoothCoefficients']");f.write_text(s)
