from pathlib import Path
p=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor/web/fit.js'
s=p.read_text().replace('relaxSurface(out,.9,region.scrotalSmoothIndices,region.scrotalSmoothNeighbors,region.scrotalSmoothWeights,96,region.scrotalSmoothCoefficients);smoothAttachment(out,.55+.45*p.attachment_smoothness,region);','metricFair(out,region.metricFairing,.004+.005*p.attachment_smoothness);')
s+='''
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
'''
p.write_text(s)
