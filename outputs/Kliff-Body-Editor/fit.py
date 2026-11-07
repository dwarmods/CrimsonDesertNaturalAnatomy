"""Validated editor parameters and shared deformation math (metres, Z up)."""
import math
LIMITS={'anatomy_height':(-30,30,0),'attachment_contour':(-8,8,0),'attachment_smoothness':(0,1,0),'shaft_base_width':(.6,1.5,1),'shaft_mid_width':(.6,1.5,1),'shaft_tip_width':(.6,1.5,1),'length':(.75,1.35,1),'testicle_size':(.7,1.4,1),'hang':(-10,35,0),'separation':(-5,15,0),'z':(-40,40,0),
        'scale':(.75,1.4,1),'width':(.75,1.3,1),'depth':(.75,1.3,1),'x':(-25,25,0),'y':(-25,25,0)}
def validate(p):
    if not isinstance(p,dict) or set(p)!=set(LIMITS):raise ValueError('Preset does not contain the required fitting controls.')
    for k,(lo,hi,_) in LIMITS.items():
        if isinstance(p[k],bool) or not isinstance(p[k],(int,float)) or not math.isfinite(p[k]) or not lo<=p[k]<=hi:raise ValueError(f'{k} is outside its supported range.')
    return p
def profile(t,p):
    if t<.5:
        x=t*2;f=x*x*(3-2*x);return p['shaft_base_width']*(1-f)+p['shaft_mid_width']*f
    x=(t-.5)*2;f=x*x*(3-2*x);return p['shaft_mid_width']*(1-f)+p['shaft_tip_width']*f
def deform(base,weights,pivot,p,region):
    validate(p);out=list(base)
    scales=[p['scale']*p['width'],p['scale']*p['depth'],p['scale']]
    offsets=[p[k]/1000 for k in ('x','y','z')]
    for i,w in enumerate(weights):
        l=region['leftWeights'][i];r=region['rightWeights'][i];s=region['shaftWeights'][i];b=min(1,l+r)
        width_delta=(profile(region['profileT'][i],p)-1)*region['profileWeights'][i]
        for a in range(3):
            j=3*i+a
            value=base[j]+((base[j]-region['leftCenter'][a])*l+(base[j]-region['rightCenter'][a])*r)*(p['testicle_size']-1)
            if a==0:value+=(base[j]-pivot[0])*width_delta
            if a==2:value+=s*(base[j]-pivot[a])*(p['length']-1)-b*p['hang']/1000
            if a==1:value+=region['attachmentWeights'][i]*p['attachment_contour']/1000-b*p['separation']/1000
            out[j]=value+region['anatomyScaleWeights'][i]*(value-pivot[a])*(scales[a]-1)+w*offsets[a]
    loft_transition(out,region)
    smooth_attachment(out,.55+.45*p['attachment_smoothness'],region)
    metric_fair(out,region['metricFairing'],.004+.005*p['attachment_smoothness'])
    # Apply after smoothing so this control cannot move torso vertices.
    for i,w in enumerate(region['anatomyHeightWeights']):out[i*3+2]+=w*p['anatomy_height']/1000
    return out

def metric_fair(out,patch,radius):
    """Implicit surface diffusion with fixed boundary and physical length scale.

    Solve (M + radius^2 L)x = M x0 using Jacobi-preconditioned CG.
    Cotangent edges are symmetric; zero/negative weights were clamped at build.
    """
    import numpy as np
    ids=np.asarray(patch['ids'],dtype=int);count=len(ids)
    rows=np.repeat(np.arange(count),[len(js) for js in patch['neighbors']])
    local=np.asarray([j for js in patch['localNeighbors'] for j in js],dtype=int)
    neighbors=np.asarray([j for js in patch['neighbors'] for j in js],dtype=int)
    coeff=np.asarray([c for cs in patch['coefficients'] for c in cs])
    mass=np.asarray(patch['mass'])/(radius*radius)
    diagonal=mass+np.bincount(rows,weights=coeff,minlength=count)
    free=local>=0;rr=rows[free];jj=local[free];cc=coeff[free]
    fixed=~free;original=np.asarray(out).reshape(-1,3)
    for axis in range(3):
        x=original[ids,axis].copy()
        rhs=mass*x+np.bincount(rows[fixed],weights=coeff[fixed]*original[neighbors[fixed],axis],minlength=count)
        def apply(v):return diagonal*v-np.bincount(rr,weights=cc*v[jj],minlength=count)
        residual=rhs-apply(x);z=residual/diagonal;direction=z.copy();rz=float(residual@z)
        for _ in range(160):
            if rz<1e-22:break
            product=apply(direction);denom=float(direction@product)
            if denom<=0:break
            step=rz/denom;x+=step*direction;residual-=step*product
            z=residual/diagonal;next_rz=float(residual@z)
            direction=z+(next_rz/rz)*direction;rz=next_rz
        original[ids,axis]=x
    out[:]=original.ravel().tolist()

def relax_surface(out,amount,ids,neighbors,weights,passes,coefficients):
    original=list(out);current=list(out)
    for step in range(passes):
        delta=[[((sum(current[j*3+a]*coefficients[k][q] for q,j in enumerate(neighbors[k])))-current[i*3+a])*.4*weights[k] for a in range(3)] for k,i in enumerate(ids)]
        for k,i in enumerate(ids):
            for a in range(3):current[i*3+a]+=delta[k][a]
    for i in ids:
        for a in range(3):
            j=i*3+a;out[j]=original[j]+amount*(current[j]-original[j])
def smooth_attachment(out,amount,r):
    relax_surface(out,amount,r['attachmentSmoothIndices'],r['attachmentSmoothNeighbors'],r['attachmentSmoothWeights'],100,r['attachmentSmoothCoefficients'])

def loft_transition(out,r):
    for q in r['transitionRows']:
        start=[out[q['inner']*3+a] for a in range(3)];end=[out[q['outerA']*3+a]*(1-q['f'])+out[q['outerB']*3+a]*q['f'] for a in range(3)]
        dx=end[0]-start[0];dz=end[2]-start[2];radial=math.hypot(dx,dz);t=q['t'];sy=sr=0
        for j in q['neighbors']:
            sy+=start[1]-out[j*3+1];sr+=((start[0]-out[j*3])*dx+(start[2]-out[j*3+2])*dz)/max(radial,1e-9)
        slope=max(-1.5,min(1.5,sy/sr)) if sr>1e-6 else 0
        normal=[r['seamNormals'][q['outerA']*3+a]*(1-q['f'])+r['seamNormals'][q['outerB']*3+a]*q['f'] for a in range(3)]
        outer_tangent=-(normal[0]*dx+normal[2]*dz)/max(.1,normal[1])
        outer_tangent=max(-1.5*radial,min(1.5*radial,outer_tangent))
        out[q['index']*3]=start[0]+dx*t;out[q['index']*3+2]=start[2]+dz*t
        out[q['index']*3+1]=(2*t*t*t-3*t*t+1)*start[1]+(t*t*t-2*t*t+t)*slope*radial+(-2*t*t*t+3*t*t)*end[1]+(t*t*t-t*t)*outer_tangent

def fair_normal_patch(normals,r,prefix):
    ids=r[prefix+'SmoothIndices'];ns=r[prefix+'SmoothNeighbors'];ws=r[prefix+'SmoothWeights'];current=list(normals);new=list(normals)
    for step in range(24):
        for k,i in enumerate(ids):
            blend=.55*ws[k]
            for a in range(3):new[i*3+a]=current[i*3+a]*(1-blend)+blend*sum(current[j*3+a] for j in ns[k])/len(ns[k])
            length=math.sqrt(sum(new[i*3+a]**2 for a in range(3))) or 1
            for a in range(3):new[i*3+a]/=length
        current=list(new)
    return current

def fair_normals(normals,r):
    return fair_normal_patch(fair_normal_patch(normals,r,'attachment'),r,'scrotal')
