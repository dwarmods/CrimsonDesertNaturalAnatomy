import sys,json,importlib.util,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent;APP=ROOT/'outputs/Kliff-Body-Editor';sys.path.insert(0,str(APP))
import fit
a=json.loads((APP/'web/assets/body.json').read_text());r=next(m for m in a['meshes'] if m['editable']);base=r['positions'];patch=r['metricFairing'];ids=patch['ids']
rows=np.repeat(np.arange(len(ids)),[len(ns) for ns in patch['neighbors']]);neighbors=np.array([j for ns in patch['neighbors'] for j in ns]);cs=np.array([c for ns in patch['coefficients'] for c in ns]);sums=np.bincount(rows,weights=cs)
def roughness(pos,selected):
 xyz=np.array(pos).reshape(-1,3);lap=np.column_stack([xyz[ids,axis]-np.bincount(rows,weights=cs*xyz[neighbors,axis])/sums for axis in range(3)])
 return float(np.sqrt(np.mean(np.sum(lap[selected]**2,axis=1))))
cases=json.loads((ROOT/'work/metric-js-results.json').read_text());errors=[]
for case in cases:
 out=fit.deform(base,r['weights'],a['pivot'],case['parameters'],r)
 error=max(abs(x-y) for x,y in zip(out,case['positions']));assert error<2e-6,error;assert all(math.isfinite(x) for x in out);errors.append(error)
# Assess the reported preset against the preceding revision on the same topology.
oldroot=ROOT/'work/editor-before-bump-repair';spec=importlib.util.spec_from_file_location('oldfit',oldroot/'fit.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
oa=json.loads((oldroot/'web/assets/body.json').read_text());orr=next(m for m in oa['meshes'] if m['editable']);p=cases[1]['parameters']
before=old.deform(orr['positions'],orr['weights'],oa['pivot'],p,orr);after=fit.deform(base,r['weights'],a['pivot'],p,r)
upper=np.array([base[3*i+2]>.925 for i in ids]);lower=np.array([.84<base[3*i+2]<.90 and r['leftWeights'][i]+r['rightWeights'][i]>.01 for i in ids])
metrics={}
for name,selection in [('upper_attachment',upper),('lower_fold',lower)]:
 pre=roughness(before,selection);post=roughness(after,selection);assert post<pre,(name,pre,post)
 metrics[name]={'before_laplacian_rms_mm':pre*1000,'after_laplacian_rms_mm':post*1000,'reduction_percent':100*(1-post/pre)}
# The metric solver cannot alter vertices outside its declared connected patch.
trial=list(base);fit.metric_fair(trial,patch,.009);outside=set(range(len(base)//3))-set(ids)
assert all(trial[3*i:3*i+3]==base[3*i:3*i+3] for i in outside)
report={'passed':True,'patch_vertices':len(ids),'js_python_max_error_metres':max(errors),'tested_presets':len(cases),'fixed_patch_boundary':True,'roughness':metrics,'relative_height':json.loads((ROOT/'work/editor-relative-height-tests.json').read_text()),'visual_review':'Same preset, lighting and front/side/oblique views compared; reduced upper lip and lower fold ridge. This is not proof of seamless textures or game compatibility.'}
(ROOT/'work/editor-bump-tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
