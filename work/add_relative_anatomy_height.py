"""Add a separate translation field confined to the attached anatomy."""
from pathlib import Path
import json,math,heapq
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor'
f=APP/'web/assets/body.json';asset=json.loads(f.read_text());r=next(m for m in asset['meshes'] if m['editable'])
positions=r['positions'];n=len(positions)//3;region=set(r['region']);adj=[set() for _ in range(n)];ix=r['indices']
for a,b,c in zip(ix[::3],ix[1::3],ix[2::3]):
 for i,j in [(a,b),(b,c),(c,a)]:
  if i in region and j in region:adj[i].add(j);adj[j].add(i)
distance=[math.inf]*n;queue=[]
for i in r['join']:
 if i in region:distance[i]=0;heapq.heappush(queue,(0,i))
while queue:
 d,i=heapq.heappop(queue)
 if d!=distance[i] or d>=.025:continue
 for j in adj[i]:
  nd=d+math.dist(positions[3*i:3*i+3],positions[3*j:3*j+3])
  if nd<distance[j]:distance[j]=nd;heapq.heappush(queue,(nd,j))
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
r['anatomyHeightWeights']=[smooth(distance[i]/.025) if i in region else 0 for i in range(n)]
f.write_text(json.dumps(asset,separators=(',',':')))
f=APP/'fit.py';s=f.read_text().replace("LIMITS={'attachment_contour'", "LIMITS={'anatomy_height':(-30,30,0),'attachment_contour'")
s=s.replace("    return out\n", "    # Apply after smoothing so this control cannot move torso vertices.\n    for i,w in enumerate(region['anatomyHeightWeights']):out[i*3+2]+=w*p['anatomy_height']/1000\n    return out\n")
f.write_text(s)
f=APP/'web/fit.js';s=f.read_text().replace('limits={attachment_contour', 'limits={anatomy_height:[-30,30,0],attachment_contour')
start=s.index('export function migrate(');end=s.index('\nconst smooth=',start)
s=s[:start]+'''export function migrate(p){
 const keys=Object.keys(limits),profile=['attachment_contour','attachment_smoothness','shaft_base_width','shaft_mid_width','shaft_tip_width','anatomy_height'];
 const versions=[keys,keys.filter(k=>k!=='anatomy_height'),keys.filter(k=>!profile.includes(k))];
 if(p&&typeof p==='object'&&!Array.isArray(p)&&versions.some(v=>v.sort().join()===Object.keys(p).sort().join()))return validate({...defaults(),...p});
 return validate(p);
}'''+s[end:]
s=s.replace('smoothAttachment(out,p.attachment_smoothness,region);return out;', 'smoothAttachment(out,p.attachment_smoothness,region);for(let i=0;i<weights.length;i++)out[i*3+2]+=region.anatomyHeightWeights[i]*p.anatomy_height/1000;return out;')
f.write_text(s)
f=APP/'web/app.js';s=f.read_text().replace("['x','y','z','hang'", "['x','y','z','anatomy_height','hang'")
s=s.replace('const info={', "const info={anatomy_height:['Anatomy height - relative to pelvis','mm','Moves shaft and testicles only; torso and attachment rim stay fixed. Negative: lower. Positive: higher.'],")
s=s.replace("z:['Pelvis placement - up / down','mm','Moves the shaft and testicles together. Negative: lower. Positive: higher.']", "z:['Pelvis + anatomy height','mm','Moves the fitted anatomy and surrounding pelvis together.']")
s=s.replace("['z',...Object.keys(limits).filter(k=>k!=='z')]", "['anatomy_height','z',...Object.keys(limits).filter(k=>!['anatomy_height','z'].includes(k))]")
s=s.replace('[0,1,6,10].includes(index)', '[0,2,7,11].includes(index)').replace("({0:'PELVIS PLACEMENT',1:'ATTACHMENT & SHAFT PROFILE',6:'ANATOMY',10:'OVERALL FIT'})", "({0:'POSITION',2:'ATTACHMENT & SHAFT PROFILE',7:'ANATOMY',11:'OVERALL FIT'})")
f.write_text(s)
f=APP/'web/index.html';s=f.read_text().replace('EDITOR 1.2','EDITOR 1.3').replace('Editor 1.2','Editor 1.3');f.write_text(s)
f=APP/'editor.py';s=f.read_text().replace("'version':'1.2.0'", "'version':'1.3.0'");f.write_text(s)
f=APP/'READ-ME.txt';s=f.read_text().replace('EDITOR 1.2','EDITOR 1.3').replace('Version 1.2 loads 1.1 presets', 'Version 1.3 loads 1.1 and 1.2 presets')
s=s.replace('CONTROLS\n', 'CONTROLS\n- Anatomy height - relative to pelvis: -30 to +30 mm. Moves the shaft and\n  scrotal region independently; torso vertices and the attachment rim stay\n  fixed, with a 25 mm transition inside the attached anatomy. This can\n  stretch or compress the attachment transition at larger displacements.\n')
s=s.replace('- Pelvis placement - up / down, at the top: moves the shaft and testicles\n  together from -40 to +40 mm; negative is lower, positive is higher.', '- Pelvis + anatomy height: the original -40 to +40 mm control, which also\n  moves the surrounding pelvis with a broad falloff.')
f.write_text(s)
print('Added independent anatomy height; torso and rim weights are zero.')
