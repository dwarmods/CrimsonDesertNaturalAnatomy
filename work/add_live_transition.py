from pathlib import Path
APP=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor'
f=APP/'web/fit.js';s=f.read_text();s=s.replace('relaxSurface(out,.65,region.scrotal', 'loftTransition(out,region);relaxSurface(out,.65,region.scrotal')
s+='''
function loftTransition(out,r){
 for(const q of r.transitionRows){
  const start=[0,1,2].map(a=>out[q.inner*3+a]),end=[0,1,2].map(a=>out[q.outerA*3+a]*(1-q.f)+out[q.outerB*3+a]*q.f);
  const dx=end[0]-start[0],dz=end[2]-start[2],radial=Math.hypot(dx,dz),t=q.t;
  let sy=0,sr=0;
  for(const j of q.neighbors){sy+=start[1]-out[j*3+1];sr+=((start[0]-out[j*3])*dx+(start[2]-out[j*3+2])*dz)/Math.max(radial,1e-9);}
  const slope=sr>1e-6?Math.max(-1.5,Math.min(1.5,sy/sr)):0;
  out[q.index*3]=start[0]+dx*t;out[q.index*3+2]=start[2]+dz*t;
  out[q.index*3+1]=(2*t*t*t-3*t*t+1)*start[1]+(t*t*t-2*t*t+t)*slope*radial+(-2*t*t*t+3*t*t)*end[1];
 }
}
''';f.write_text(s)
f=APP/'fit.py';s=f.read_text().replace("    relax_surface(out,.65,region['scrotal", "    loft_transition(out,region)\n    relax_surface(out,.65,region['scrotal")
s+='''
def loft_transition(out,r):
    for q in r['transitionRows']:
        start=[out[q['inner']*3+a] for a in range(3)];end=[out[q['outerA']*3+a]*(1-q['f'])+out[q['outerB']*3+a]*q['f'] for a in range(3)]
        dx=end[0]-start[0];dz=end[2]-start[2];radial=math.hypot(dx,dz);t=q['t'];sy=sr=0
        for j in q['neighbors']:
            sy+=start[1]-out[j*3+1];sr+=((start[0]-out[j*3])*dx+(start[2]-out[j*3+2])*dz)/max(radial,1e-9)
        slope=max(-1.5,min(1.5,sy/sr)) if sr>1e-6 else 0
        out[q['index']*3]=start[0]+dx*t;out[q['index']*3+2]=start[2]+dz*t
        out[q['index']*3+1]=(2*t*t*t-3*t*t+1)*start[1]+(t*t*t-2*t*t+t)*slope*radial+(-2*t*t*t+3*t*t)*end[1]
''';f.write_text(s)
