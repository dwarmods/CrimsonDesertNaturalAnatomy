"""Export LOCAL editor data and Python references for the native fitting backend.

Generated files contain game-derived mesh data. Keep them outside Git.
Usage: python work/build_native_fit_fixtures.py --asset <body.json> --out <folder>
"""
from pathlib import Path
import argparse, importlib.util, json, struct, time

def build(asset_path, out):
    root=Path(__file__).resolve().parent.parent
    spec=importlib.util.spec_from_file_location('editor_fit',root/'outputs/Kliff-Body-Editor/fit.py')
    fit=importlib.util.module_from_spec(spec);spec.loader.exec_module(fit)
    asset=json.loads(asset_path.read_text());r=next(m for m in asset['meshes'] if m['editable'])
    n=len(r['weights']);assert len(r['positions'])==3*n
    out.mkdir(parents=True,exist_ok=True)
    fields=('weights','leftWeights','rightWeights','shaftWeights','profileT','profileWeights',
            'attachmentWeights','anatomyScaleWeights','anatomyHeightWeights')
    with (out/'body.nafit').open('wb') as f:
        def pack(fmt,*values):f.write(struct.pack('<'+fmt,*values))
        def doubles(values):pack(str(len(values))+'d',*values)
        def edges(indices,coefficients):
            assert len(indices)==len(coefficients);pack('I',len(indices))
            for i,c in zip(indices,coefficients):pack('Id',i,c)
        f.write(b'NAFIT01!');pack('I',n);doubles(r['positions'])
        for center in (asset['pivot'],r['leftCenter'],r['rightCenter']):doubles(center)
        for name in fields:
            assert len(r[name])==n;doubles(r[name])
        doubles(r['seamNormals'])
        ids=r['attachmentSmoothIndices'];pack('I',len(ids))
        for k,i in enumerate(ids):
            pack('Id',i,r['attachmentSmoothWeights'][k])
            edges(r['attachmentSmoothNeighbors'][k],r['attachmentSmoothCoefficients'][k])
        pack('I',len(r['transitionRows']))
        for q in r['transitionRows']:
            pack('IIIIddI',q['index'],q['inner'],q['outerA'],q['outerB'],q['f'],q['t'],len(q['neighbors']))
            for i in q['neighbors']:pack('I',i)
        metric=r['metricFairing'];pack('I',len(metric['ids']))
        for k,i in enumerate(metric['ids']):
            pack('Id',i,metric['mass'][k]);edges(metric['neighbors'][k],metric['coefficients'][k])
    defaults={k:v[2] for k,v in fit.LIMITS.items()};cases=[defaults]
    for key,(lo,hi,_) in fit.LIMITS.items():
        for value in (lo,hi):cases.append(dict(defaults,**{key:value}))
    saved=json.loads((root/'presets/neutral-fit.json').read_text())['parameters'];cases.append(saved)
    cases += [{k:v[0] for k,v in fit.LIMITS.items()},{k:v[1] for k,v in fit.LIMITS.items()}]
    with (out/'reference.bin').open('wb') as f:
        f.write(struct.pack('<II',len(cases),n))
        for index,p in enumerate(cases):
            started=time.perf_counter();positions=fit.deform(r['positions'],r['weights'],asset['pivot'],p,r)
            f.write(struct.pack('<16d',*(p[k] for k in fit.LIMITS)))
            f.write(struct.pack('<'+str(len(positions))+'d',*positions))
            print(f'{index+1}/{len(cases)} reference cases ({time.perf_counter()-started:.2f}s)',flush=True)
    print(json.dumps({'vertices':n,'cases':len(cases),'output':str(out)}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--asset',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();build(args.asset,args.out)
