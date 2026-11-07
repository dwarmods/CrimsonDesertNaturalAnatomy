"""Add local shape-control fields without altering the neutral mesh or rig."""
import json, math, heapq
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
APP=ROOT/'outputs/Kliff-Body-Editor'
assetpath=APP/'web/assets/body.json'
asset=json.loads(assetpath.read_text());row=next(m for m in asset['meshes'] if m['editable'])
p=row['positions'];n=len(p)//3;anatomy=set(row['region'])
adj=[set() for _ in range(n)];ix=row['indices']
for a,b,c in zip(ix[::3],ix[1::3],ix[2::3]):
    for i,j in [(a,b),(b,c),(c,a)]:adj[i].add(j);adj[j].add(i)
inner=[i for i in row['join'] if i in anatomy]
dist=[math.inf]*n;queue=[]
for i in inner:dist[i]=0;heapq.heappush(queue,(0,i))
while queue:
    d,i=heapq.heappop(queue)
    if d!=dist[i] or d>.055:continue
    for j in adj[i]:
        nd=d+math.dist(p[3*i:3*i+3],p[3*j:3*j+3])
        if nd<dist[j]:dist[j]=nd;heapq.heappush(queue,(nd,j))
def smooth(x):
    x=max(0,min(1,x));return x*x*(3-2*x)
shaft=[i for i,w in enumerate(row['shaftWeights']) if w>.99]
tip_z=min(p[3*i+2] for i in shaft);root_z=asset['pivot'][2]
row['profileT']=[max(0,min(1,(root_z-p[3*i+2])/(root_z-tip_z))) for i in range(n)]
row['attachmentWeights']=[];row['profileWeights']=[]
for i in range(n):
    exclude=1-smooth((row['leftWeights'][i]+row['rightWeights'][i])/.35)
    row['attachmentWeights'].append(smooth(1-dist[i]/.055)*exclude)
    row['profileWeights'].append(max(row['shaftWeights'][i],smooth(1-dist[i]/.03)*exclude))
assetpath.write_text(json.dumps(asset,separators=(',',':')))
backup=ROOT/'outputs/Kliff-fit-before-editor-update-v03.json'
if not backup.exists():backup.write_text(json.dumps({'schema':1,'asset':'kliff-connected-v03','parameters':{'scale':1.4,'width':1.3,'depth':1.2,'height':1.2,'x':0,'y':-11,'z':-29.5}},indent=2))
print(json.dumps({'vertices':n,'join_seeds':len(inner),'contour_vertices':sum(w>0 for w in row['attachmentWeights']),'profile_vertices':sum(w>0 for w in row['profileWeights'])}))

fitjs=APP/'web/fit.js'
s=fitjs.read_text()
s=s.replace('limits={length:', 'limits={attachment_contour:[-8,8,0],shaft_base_width:[.6,1.5,1],shaft_mid_width:[.6,1.5,1],shaft_tip_width:[.6,1.5,1],length:')
s=s.replace('export function deform(', '''export function migrate(p){const legacy=Object.keys(limits).filter(k=>!['attachment_contour','shaft_base_width','shaft_mid_width','shaft_tip_width'].includes(k));if(p&&typeof p==='object'&&Object.keys(p).sort().join()===legacy.sort().join())return validate({...defaults(),...p});return validate(p);}
const smooth=x=>x*x*(3-2*x);
export function profile(t,p){if(t<.5){const f=smooth(t*2);return p.shaft_base_width*(1-f)+p.shaft_mid_width*f;}const f=smooth((t-.5)*2);return p.shaft_mid_width*(1-f)+p.shaft_tip_width*f;}
export function deform(''')
s=s.replace('for(let a=0;a<3;a++){const j=3*i+a;', 'const widthDelta=(profile(region.profileT[i],p)-1)*region.profileWeights[i];for(let a=0;a<3;a++){const j=3*i+a;')
s=s.replace('if(a===2)value+=', 'if(a===0)value+=(base[j]-pivot[0])*widthDelta;if(a===2)value+=')
s=s.replace('if(a===1)value-=b*p.separation/1000;', 'if(a===1)value+=region.attachmentWeights[i]*p.attachment_contour/1000-b*p.separation/1000;')
fitjs.write_text(s)
f=APP/'fit.py';s=f.read_text()
s=s.replace("LIMITS={'length':", "LIMITS={'attachment_contour':(-8,8,0),'shaft_base_width':(.6,1.5,1),'shaft_mid_width':(.6,1.5,1),'shaft_tip_width':(.6,1.5,1),'length':")
s=s.replace('def deform(', '''def profile(t,p):
    if t<.5:
        x=t*2;f=x*x*(3-2*x);return p['shaft_base_width']*(1-f)+p['shaft_mid_width']*f
    x=(t-.5)*2;f=x*x*(3-2*x);return p['shaft_mid_width']*(1-f)+p['shaft_tip_width']*f
def deform(''')
s=s.replace('        for a in range(3):', "        width_delta=(profile(region['profileT'][i],p)-1)*region['profileWeights'][i]\n        for a in range(3):")
s=s.replace('            if a==2:', "            if a==0:value+=(base[j]-pivot[0])*width_delta\n            if a==2:")
s=s.replace("if a==1:value-=b*p['separation']/1000", "if a==1:value+=region['attachmentWeights'][i]*p['attachment_contour']/1000-b*p['separation']/1000")
f.write_text(s)

f=APP/'web/app.js';s=f.read_text()
s=s.replace('limits,defaults,validate,deform', 'limits,defaults,validate,migrate,deform')
s=s.replace("['x','y','z','hang','separation']", "['x','y','z','hang','separation','attachment_contour']")
s=s.replace('return validate(data.parameters);', 'return migrate(data.parameters);')
s=s.replace("const info={length:", "const info={attachment_contour:['Attachment contour','mm','Negative: concave / recessed. Positive: convex / raised.'],shaft_base_width:['Shaft width - base','%','Side-to-side width at the attachment; blends into the torso.'],shaft_mid_width:['Shaft width - middle','%','Side-to-side width halfway along the shaft.'],shaft_tip_width:['Shaft width - tip','%','Side-to-side width at the end.'],length:")
s=s.replace("if(index===0||index===5){const h=document.createElement('div');h.className='section-title';h.textContent=index===0?'ANATOMY & PLACEMENT':'OVERALL FIT';$('controls').append(h);}", "if([0,4,9].includes(index)){const h=document.createElement('div');h.className='section-title';h.textContent=index===0?'ATTACHMENT & SHAFT PROFILE':index===4?'ANATOMY & PLACEMENT':'OVERALL FIT';$('controls').append(h);}")
s=s.replace('const w=bodyRow.seamNormalWeights[i];', 'const w=bodyRow.seamNormalWeights[i]*Math.max(0,1-Math.abs(params.attachment_contour)/2);')
s=s.replace("if(!body)return;", "if(!body)return;")
f.write_text(s)
f=APP/'export_blend.py';s=f.read_text().replace("w=row['seamNormalWeights'][i]", "w=row['seamNormalWeights'][i]*max(0,1-abs(p['attachment_contour'])/2)");f.write_text(s)
f=APP/'web/index.html';s=f.read_text().replace('BODY EDITOR</span>','BODY EDITOR 1.2</span>').replace('Kliff body draft v0.4','Editor 1.2 · Body draft v0.4');f.write_text(s)
f=APP/'editor.py';s=f.read_text().replace("'version':'1.1.0'", "'version':'1.2.0'")
s=s.replace('    def log_message(self,*a):pass', "    def end_headers(self):\n        self.send_header('Cache-Control','no-store')\n        super().end_headers()\n    def log_message(self,*a):pass")
f.write_text(s)
