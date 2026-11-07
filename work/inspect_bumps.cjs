const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1400,height:1000}});
 if(process.argv.includes('--strong'))await page.route('**/fit.js',route=>route.fulfill({contentType:'application/javascript',body:fs.readFileSync('outputs/Kliff-Body-Editor/web/fit.js','utf8').replace('.004+.005*p.attachment_smoothness','.006+.010*p.attachment_smoothness')}));
 if(process.argv.includes('--raw-normals'))await page.route('**/app.js',route=>{let s=fs.readFileSync('outputs/Kliff-Body-Editor/web/app.js','utf8');const start=s.indexOf('for(let i=0;i<bodyRow.seamNormalWeights.length;i++)'),end=s.indexOf('body.geometry.attributes.normal.needsUpdate=true',start);s=s.slice(0,start)+s.slice(end);return route.fulfill({contentType:'application/javascript',body:s});});
 await page.goto('http://127.0.0.1:48763/');await page.waitForFunction(()=>window.editorReady);
 const defaults=(await page.evaluate(()=>window.editorSnapshot())).parameters;
 const p={...defaults,anatomy_height:-7.5,attachment_contour:-3.5,attachment_smoothness:1,shaft_base_width:.86,shaft_mid_width:1.5,shaft_tip_width:1.25,length:1.35,testicle_size:1.4,hang:30.5,separation:15,z:-11,scale:1.4,width:1.3,depth:1.3,x:0,y:-3.5};
 fs.writeFileSync('work/bump-fit.json',JSON.stringify({schema:1,asset:'kliff-connected-v04',parameters:p},null,2));
 await page.locator('#presetfile').setInputFiles('work/bump-fit.json');await page.locator('#focus').click();
 const tag=process.argv[2]||'inspect';
 const box=await page.locator('#canvas').boundingBox();
 // Same camera and light for every revision; tighter crop through normal orbit zoom.
 await page.mouse.move(box.width*.5,box.y+box.height*.5);await page.mouse.wheel(0,-400);await page.waitForTimeout(500);
 for(const [view,delta] of [['front',0],['oblique',-135],['side',0]]){
  await page.locator('[data-view="'+(view==='oblique'?'side':view)+'"]').click();
  await page.mouse.move(box.width*.5,box.y+box.height*.5);await page.mouse.wheel(0,-400);
  if(delta){await page.mouse.down();await page.mouse.move(box.width*.5+delta,box.y+box.height*.5,{steps:20});await page.mouse.up();}
  await page.waitForTimeout(700);await page.screenshot({path:`work/bump-${tag}-${view}.png`});
 }
 await browser.close();
})();
