export const limits={anatomy_height:[-30,30,0],attachment_contour:[-8,8,0],attachment_smoothness:[0,1,0],shaft_base_width:[.6,1.5,1],shaft_mid_width:[.6,1.5,1],shaft_tip_width:[.6,1.5,1],length:[.75,1.35,1],testicle_size:[.7,1.4,1],hang:[-10,35,0],separation:[-5,15,0],z:[-40,40,0],scale:[.75,1.4,1],width:[.75,1.3,1],depth:[.75,1.3,1],x:[-25,25,0],y:[-25,25,0]};
export const defaults=()=>Object.fromEntries(Object.entries(limits).map(([k,v])=>[k,v[2]]));
export function validate(p){if(!p||typeof p!=='object'||Array.isArray(p)||Object.keys(p).sort().join()!=Object.keys(limits).sort().join())throw Error('Preset does not contain the required fitting controls.');for(const [k,[lo,hi]] of Object.entries(limits))if(typeof p[k]!=='number'||!Number.isFinite(p[k])||p[k]<lo||p[k]>hi)throw Error(`${k} is outside its supported range.`);return {...p};}
export function migrate(p){
 const keys=Object.keys(limits),profile=['attachment_contour','attachment_smoothness','shaft_base_width','shaft_mid_width','shaft_tip_width','anatomy_height'];
 const versions=[keys,keys.filter(k=>k!=='anatomy_height'),keys.filter(k=>!profile.includes(k))];
 if(p&&typeof p==='object'&&!Array.isArray(p)&&versions.some(v=>v.sort().join()===Object.keys(p).sort().join()))return validate({...defaults(),...p});
 return validate(p);
}
const smooth=x=>x*x*(3-2*x);
export function profile(t,p){if(t<.5){const f=smooth(t*2);return p.shaft_base_width*(1-f)+p.shaft_mid_width*f;}const f=smooth((t-.5)*2);return p.shaft_mid_width*(1-f)+p.shaft_tip_width*f;}
export function deform(base,weights,pivot,p,region,out=new Float32Array(base.length)){validate(p);out.set(base);const scales=[p.scale*p.width,p.scale*p.depth,p.scale],offsets=[p.x/1000,p.y/1000,p.z/1000];for(let i=0;i<weights.length;i++){const l=region.leftWeights[i],r=region.rightWeights[i],s=region.shaftWeights[i],b=Math.min(1,l+r);const widthDelta=(profile(region.profileT[i],p)-1)*region.profileWeights[i];for(let a=0;a<3;a++){const j=3*i+a;let value=base[j]+((base[j]-region.leftCenter[a])*l+(base[j]-region.rightCenter[a])*r)*(p.testicle_size-1);if(a===0)value+=(base[j]-pivot[0])*widthDelta;if(a===2)value+=s*(base[j]-pivot[a])*(p.length-1)-b*p.hang/1000;if(a===1)value+=region.attachmentWeights[i]*p.attachment_contour/1000-b*p.separation/1000;out[j]=value+region.anatomyScaleWeights[i]*(value-pivot[a])*(scales[a]-1)+weights[i]*offsets[a];}}loftTransition(out,region);smoothAttachment(out,.55+.45*p.attachment_smoothness,region);metricFair(out,region.metricFairing,.004+.005*p.attachment_smoothness);for(let i=0;i<weights.length;i++)out[i*3+2]+=region.anatomyHeightWeights[i]*p.anatomy_height/1000;return out;}

// Geometry fairing of a connected patch with fixed boundaries.
export function relaxSurface(out,amount,ids,neighbors,weights,passes,coefficients){
 const original=new Float64Array(out),current=new Float64Array(out),delta=new Float64Array(ids.length*3);
 for(let pass=0;pass<passes;pass++){
  for(let k=0;k<ids.length;k++)for(let a=0;a<3;a++){
   let sum=0;for(let q=0;q<neighbors[k].length;q++)sum+=current[neighbors[k][q]*3+a]*coefficients[k][q];
   delta[k*3+a]=(sum-current[ids[k]*3+a])*.4*weights[k];
  }
  for(let k=0;k<ids.length;k++)for(let a=0;a<3;a++)current[ids[k]*3+a]+=delta[k*3+a];
 }
 for(const i of ids)for(let a=0;a<3;a++){const j=i*3+a;out[j]=original[j]+amount*(current[j]-original[j]);}
}
export function smoothAttachment(out,amount,r){relaxSurface(out,amount,r.attachmentSmoothIndices,r.attachmentSmoothNeighbors,r.attachmentSmoothWeights,100,r.attachmentSmoothCoefficients);}

function loftTransition(out,r){
 for(const q of r.transitionRows){
  const start=[0,1,2].map(a=>out[q.inner*3+a]),end=[0,1,2].map(a=>out[q.outerA*3+a]*(1-q.f)+out[q.outerB*3+a]*q.f);
  const dx=end[0]-start[0],dz=end[2]-start[2],radial=Math.hypot(dx,dz),t=q.t;
  let sy=0,sr=0;
  for(const j of q.neighbors){sy+=start[1]-out[j*3+1];sr+=((start[0]-out[j*3])*dx+(start[2]-out[j*3+2])*dz)/Math.max(radial,1e-9);}
  const slope=sr>1e-6?Math.max(-1.5,Math.min(1.5,sy/sr)):0;
  const normal=[0,1,2].map(a=>r.seamNormals[q.outerA*3+a]*(1-q.f)+r.seamNormals[q.outerB*3+a]*q.f);
  const outerTangent=Math.max(-1.5*radial,Math.min(1.5*radial,-(normal[0]*dx+normal[2]*dz)/Math.max(.1,normal[1])));
  out[q.index*3]=start[0]+dx*t;out[q.index*3+2]=start[2]+dz*t;
  out[q.index*3+1]=(2*t*t*t-3*t*t+1)*start[1]+(t*t*t-2*t*t+t)*slope*radial+(-2*t*t*t+3*t*t)*end[1]+(t*t*t-t*t)*outerTangent;
 }
}

function fairNormalPatch(normals,r,prefix){
 const ids=r[prefix+'SmoothIndices'],ns=r[prefix+'SmoothNeighbors'],ws=r[prefix+'SmoothWeights'],current=new Float64Array(normals),next=new Float64Array(normals);
 for(let pass=0;pass<24;pass++){
  for(let k=0;k<ids.length;k++){
   const i=ids[k],blend=.55*ws[k];let length=0;
   for(let a=0;a<3;a++){let sum=0;for(const j of ns[k])sum+=current[j*3+a];next[i*3+a]=current[i*3+a]*(1-blend)+blend*sum/ns[k].length;length+=next[i*3+a]**2;}
   length=Math.sqrt(length);for(let a=0;a<3;a++)next[i*3+a]/=length||1;
  }
  current.set(next);
 }
 normals.set(current);
}

export function fairNormals(normals,r){fairNormalPatch(normals,r,'attachment');fairNormalPatch(normals,r,'scrotal');}

// Metric implicit fairing: identical fixed-boundary solve to the Blender exporter.
export function metricFair(out,patch,radius){
 const ids=patch.ids,n=ids.length,ns=patch.neighbors,local=patch.localNeighbors,cs=patch.coefficients;
 const mass=new Float64Array(n),diagonal=new Float64Array(n);
 for(let k=0;k<n;k++){mass[k]=patch.mass[k]/(radius*radius);diagonal[k]=mass[k]+cs[k].reduce((a,b)=>a+b,0);}
 const x=new Float64Array(n),rhs=new Float64Array(n),residual=new Float64Array(n),z=new Float64Array(n),direction=new Float64Array(n),product=new Float64Array(n);
 function apply(v,result){for(let k=0;k<n;k++){let value=diagonal[k]*v[k];for(let q=0;q<local[k].length;q++){const j=local[k][q];if(j>=0)value-=cs[k][q]*v[j];}result[k]=value;}}
 function dot(a,b){let v=0;for(let i=0;i<n;i++)v+=a[i]*b[i];return v;}
 for(let axis=0;axis<3;axis++){
  for(let k=0;k<n;k++){x[k]=out[ids[k]*3+axis];rhs[k]=mass[k]*x[k];for(let q=0;q<ns[k].length;q++)if(local[k][q]<0)rhs[k]+=cs[k][q]*out[ns[k][q]*3+axis];}
  apply(x,product);for(let k=0;k<n;k++){residual[k]=rhs[k]-product[k];z[k]=residual[k]/diagonal[k];direction[k]=z[k];}
  let rz=dot(residual,z);
  for(let pass=0;pass<160&&rz>=1e-22;pass++){
   apply(direction,product);const denom=dot(direction,product);if(denom<=0)break;const step=rz/denom;
   for(let k=0;k<n;k++){x[k]+=step*direction[k];residual[k]-=step*product[k];z[k]=residual[k]/diagonal[k];}
   const next=dot(residual,z),beta=next/rz;for(let k=0;k<n;k++)direction[k]=z[k]+beta*direction[k];rz=next;
  }
  for(let k=0;k<n;k++)out[ids[k]*3+axis]=x[k];
 }
}
