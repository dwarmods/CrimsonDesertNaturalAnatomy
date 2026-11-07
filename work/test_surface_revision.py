import json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor';sys.path.insert(0,str(APP));import fit
a=json.loads((APP/'web/assets/body.json').read_text());r=next(m for m in a['meshes'] if m['editable']);p=json.loads((ROOT/'work/current-fold-fit.json').read_text())['parameters'];p['attachment_smoothness']=1
original=fit.relax_surface;metrics=[]
def checked(out,amount,ids,neighbors,weights,passes,coefficients):
 def energy():
  return sum(sum((out[i*3+k]-sum(out[j*3+k]*coefficients[v][q] for q,j in enumerate(neighbors[v])))**2 for k in range(3)) for v,i in enumerate(ids) if weights[v]>.5)
 before=energy();original(out,amount,ids,neighbors,weights,passes,coefficients);after=energy()
 metrics.append({'patch_vertices':len(ids),'curvature_energy_before':before,'curvature_energy_after':after,'reduction_fraction':1-after/before})
 assert after<before
fit.relax_surface=checked
out=fit.deform(r['positions'],r['weights'],a['pivot'],p,r)
assert all(math.isfinite(v) for v in out)
inner=[i for i in r['join'] if i in set(r['region'])]
assert all(r['attachmentWeights'][i]==1 for i in inner)
report={'passed':True,'geometry_fairing':metrics,'contour_entire_inner_circumference_has_equal_weight':True,'topology':json.loads((ROOT/'work/editor-surface-topology.json').read_text()),'relative_height':json.loads((ROOT/'work/editor-relative-height-tests.json').read_text()),'limitations':['Static editor; game integration and runtime physics unfinished','Preserved rig groups require separate rig authoring','Extreme combined fits can still distort the attachment; visual perfection is not established']}
(ROOT/'work/editor-surface-tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
