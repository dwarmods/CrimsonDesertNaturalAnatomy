import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor';f=APP/'web/assets/body.json';a=json.loads(f.read_text());r=next(m for m in a['meshes'] if m['editable']);old=json.loads((ROOT/'work/editor-before-surface-repair/web/assets/body.json').read_text());old=next(m for m in old['meshes'] if m['editable'])
# Keep the original semantic partition; a wider mask distorted the connection.
for key in ['positions','leftWeights','rightWeights','shaftWeights']:r[key][:len(old[key])]=old[key]
r['leftCenter']=old['leftCenter'];r['rightCenter']=old['rightCenter'];f.write_text(json.dumps(a,separators=(',',':')))
f=APP/'web/fit.js';s=f.read_text();s+='''
export function fairNormals(normals,r){
 const ids=r.attachmentSmoothIndices,ns=r.attachmentSmoothNeighbors,ws=r.attachmentSmoothWeights,current=new Float64Array(normals),next=new Float64Array(normals);
 for(let pass=0;pass<24;pass++){
  for(let k=0;k<ids.length;k++){
   const i=ids[k],blend=.55*ws[k];let length=0;
   for(let a=0;a<3;a++){let sum=0;for(const j of ns[k])sum+=current[j*3+a];next[i*3+a]=current[i*3+a]*(1-blend)+blend*sum/ns[k].length;length+=next[i*3+a]**2;}
   length=Math.sqrt(length);for(let a=0;a<3;a++)next[i*3+a]/=length||1;
  }
  current.set(next);
 }
 normals.set(current);
}
''';f.write_text(s)
f=APP/'web/app.js';s=f.read_text().replace('migrate,deform}', 'migrate,deform,fairNormals}').replace('body.geometry.attributes.normal.needsUpdate=true;', 'fairNormals(normals,bodyRow);body.geometry.attributes.normal.needsUpdate=true;');f.write_text(s)
f=APP/'fit.py';s=f.read_text();s+='''
def fair_normals(normals,r):
    ids=r['attachmentSmoothIndices'];ns=r['attachmentSmoothNeighbors'];ws=r['attachmentSmoothWeights'];current=list(normals);new=list(normals)
    for step in range(24):
        for k,i in enumerate(ids):
            blend=.55*ws[k]
            for a in range(3):new[i*3+a]=current[i*3+a]*(1-blend)+blend*sum(current[j*3+a] for j in ns[k])/len(ns[k])
            length=math.sqrt(sum(new[i*3+a]**2 for a in range(3))) or 1
            for a in range(3):new[i*3+a]/=length
        current=list(new)
    return current
''';f.write_text(s)
f=APP/'export_blend.py';s=f.read_text().replace('from fit import validate,deform', 'from fit import validate,deform,fair_normals').replace('ob.data.normals_split_custom_set_from_vertices(normals)', "flat=fair_normals([a for n in normals for a in n],row)\nob.data.normals_split_custom_set_from_vertices([flat[i:i+3] for i in range(0,len(flat),3)])");f.write_text(s)
