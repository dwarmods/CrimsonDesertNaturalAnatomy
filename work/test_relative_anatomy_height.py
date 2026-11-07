import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor';sys.path.insert(0,str(APP))
from fit import deform,LIMITS
a=json.loads((APP/'web/assets/body.json').read_text());r=next(m for m in a['meshes'] if m['editable']);b=r['positions'];n=len(b)//3;region=set(r['region'])
defaults={k:v[2] for k,v in LIMITS.items()}
for smoothing in [0,1]:
 p=dict(defaults,attachment_smoothness=smoothing,scale=1.4,width=1.3,depth=1.3,length=1.35,testicle_size=1.4,hang=35,separation=15,z=-11)
 before=deform(b,r['weights'],a['pivot'],p,r)
 for amount in [-30,15,30]:
  after=deform(b,r['weights'],a['pivot'],dict(p,anatomy_height=amount),r)
  assert all(after[3*i:3*i+3]==before[3*i:3*i+3] for i in range(n) if i not in region),'Torso moved'
  assert all(after[3*i:3*i+3]==before[3*i:3*i+3] for i in r['join']),'Attachment rim moved'
  core=[i for i,w in enumerate(r['anatomyHeightWeights']) if w==1]
  assert core
  assert max(abs(after[3*i+2]-before[3*i+2]-amount/1000) for i in core)<1e-12
  assert all(after[3*i:3*i+2]==before[3*i:3*i+2] for i in range(n))
report={'passed':True,'checks':['Torso vertices unchanged, including with smoothing enabled','Attachment rim stays fixed','Core anatomy translates by exact requested millimetres, regardless of overall scale','No width/depth changes'],'core_vertices':len(core)}
(ROOT/'work/editor-relative-height-tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
