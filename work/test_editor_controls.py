import sys,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor';sys.path.insert(0,str(APP))
from fit import deform,LIMITS
asset=json.loads((APP/'web/assets/body.json').read_text());row=next(m for m in asset['meshes'] if m['editable']);base=row['positions'];default={k:v[2] for k,v in LIMITS.items()}
def run(**changes):return deform(base,row['weights'],asset['pivot'],dict(default,**changes),row)
assert run()==base
core_ball=[i for i in range(len(row['weights'])) if row['leftWeights'][i]+row['rightWeights'][i]>.6]
core_shaft=[i for i in range(len(row['weights'])) if row['shaftWeights'][i]>.99 and row['leftWeights'][i]+row['rightWeights'][i]==0]
assert core_ball and core_shaft
length=run(length=1.3)
assert all(length[3*i+a]==base[3*i+a] for i in core_ball for a in range(3))
assert max(abs(length[3*i+2]-base[3*i+2]) for i in core_shaft)>.01
for options in [dict(testicle_size=1.3),dict(hang=20),dict(separation=12)]:
 values=run(**options)
 assert all(values[3*i+a]==base[3*i+a] for i in core_shaft for a in range(3))
 assert max(abs(values[3*i+a]-base[3*i+a]) for i in core_ball for a in range(3))>.001
for key,(lo,hi,_) in LIMITS.items():
 for value in [lo,hi]:assert all(math.isfinite(v) for v in run(**{key:value}))
for key in ['shaft_base_width','shaft_mid_width','shaft_tip_width','attachment_contour']:
 values=run(**{key:5 if key=='attachment_contour' else 1.4})
 assert all(values[3*i+a]==base[3*i+a] for i in core_ball for a in range(3)),key
 assert max(abs(v-b) for v,b in zip(values,base))>.001,key
 for i in range(len(row['weights'])):
  if key!='attachment_contour':assert values[3*i+1:3*i+3]==base[3*i+1:3*i+3],key
  else:assert values[3*i]==base[3*i] and values[3*i+2]==base[3*i+2],key
negative=run(attachment_contour=-8);positive=run(attachment_contour=8)
assert max(abs(a+b-2*c) for a,b,c in zip(negative,positive,base))<1e-14
smooth=run(attachment_smoothness=1);smooth_ids=set(row['attachmentSmoothIndices'])
assert max(abs(v-b) for v,b in zip(smooth,base))>.00001
assert all(smooth[3*i:3*i+3]==base[3*i:3*i+3] for i in range(len(row['weights'])) if i not in smooth_ids)
# A symmetric synthetic ring verifies that every circumferential position uses
# the same isotropic smoothing rule, independently of this asymmetric body.
from fit import smooth_attachment
N=32;synthetic=[]
for z in [-.02,0,.02]:
 for i in range(N):
  angle=2*math.pi*i/N;radius=.025 if z else .03
  synthetic.extend([radius*math.cos(angle),radius*math.sin(angle),z])
test={'attachmentSmoothIndices':list(range(N,2*N)),'attachmentSmoothNeighbors':[[N+(i-1)%N,N+(i+1)%N,i,2*N+i] for i in range(N)],'attachmentSmoothWeights':[1]*N}
smooth_attachment(synthetic,1,test)
radii=[math.hypot(synthetic[3*i],synthetic[3*i+1]) for i in range(N,2*N)]
assert max(radii)-min(radii)<1e-14
clearance=run(separation=10)
assert all(clearance[3*i]==base[3*i] and clearance[3*i+2]==base[3*i+2] for i in range(len(row['weights'])))
report={'passed':True,'checks':['Default is identity','Shaft length leaves core scrotal geometry unchanged','Testicle size/hang/separation leave core shaft unchanged','Separation changes front/back clearance only','All slider endpoints produce finite coordinates'],'core_scrotal_vertices':len(core_ball),'core_shaft_vertices':len(core_shaft),'asset':asset['asset']}
report['checks']+=['Base/middle/tip widths change X only and spare core scrotal tissue','Signed contour is localized, reversible and Y-only','Smoothing changes geometry only inside attachment field','Smoothing preserves circumferential symmetry on a symmetric ring']
(ROOT/'work/editor-control-tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
