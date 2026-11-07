import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor';f=APP/'web/assets/body.json';a=json.loads(f.read_text());r=next(m for m in a['meshes'] if m['editable']);p=r['positions'];region=set(r['region'])
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
changed=0;max_delta=0
for i in region:
 l=r['leftWeights'][i];rr=r['rightWeights'][i];b=min(1,l+rr)
 if b<=1e-8:continue
 target=smooth(b/.2)*r['anatomyHeightWeights'][i]
 # Keep original cores, expand the transition over the scrotal skin envelope.
 target=max(b,target);nl=l*target/b;nr=rr*target/b
 delta=target-b;max_delta=max(max_delta,delta)
 p[3*i+1]-=.003*delta;p[3*i+2]-=.024*delta+.0025*(nl-l)
 r['leftWeights'][i]=nl;r['rightWeights'][i]=nr
 r['shaftWeights'][i]*=1-target
 changed+=delta>1e-6
for side,key in [('left','leftCenter'),('right','rightCenter')]:
 weights=r[side+'Weights'];total=sum(weights);r[key]=[sum(p[3*i+j]*w for i,w in enumerate(weights))/total for j in range(3)]
f.write_text(json.dumps(a,separators=(',',':')))
print('Scrotal envelope weights adjusted:',changed,'maximum increase',max_delta)
