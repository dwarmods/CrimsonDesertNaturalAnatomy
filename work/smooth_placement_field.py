import json,math
from pathlib import Path
APP=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor';f=APP/'web/assets/body.json';a=json.loads(f.read_text());r=next(m for m in a['meshes'] if m['editable']);p=r['positions'];region=set(r['region']);inner=[p[3*i:3*i+3] for i in r['join'] if i in region]
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
for i in range(len(r['weights'])):
 if i in region:r['weights'][i]=1;continue
 point=p[3*i:3*i+3];d=min(math.dist(point,q) for q in inner)
 r['weights'][i]=smooth(1-d/.1)
f.write_text(json.dumps(a,separators=(',',':')))
