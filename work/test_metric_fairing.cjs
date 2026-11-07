const fs=require('fs');
(async()=>{
 const fit=await import('data:text/javascript;base64,'+fs.readFileSync('outputs/Kliff-Body-Editor/web/fit.js').toString('base64'));
 const a=JSON.parse(fs.readFileSync('outputs/Kliff-Body-Editor/web/assets/body.json')),r=a.meshes.find(m=>m.editable),current=JSON.parse(fs.readFileSync('work/bump-fit.json')).parameters;
 const cases=[fit.defaults(),current,{...current,attachment_smoothness:0,anatomy_height:30},{...current,attachment_contour:8,anatomy_height:-30}];
 const result=cases.map(p=>{const start=performance.now(),out=fit.deform(r.positions,r.weights,a.pivot,p,r);return {parameters:p,positions:Array.from(out),milliseconds:performance.now()-start};});
 fs.writeFileSync('work/metric-js-results.json',JSON.stringify(result));console.log('JS deformation cases:',result.map(x=>Math.round(x.milliseconds)+'ms').join(', '));
})();
