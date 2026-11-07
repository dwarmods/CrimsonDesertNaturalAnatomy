const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
const browser=await chromium.launch({headless:true,channel:'msedge'});const page=await browser.newPage({viewport:{width:1400,height:1000}});
await page.goto('http://127.0.0.1:48763/');await page.waitForFunction(()=>window.editorReady);
const defaults=(await page.evaluate(()=>window.editorSnapshot())).parameters;
const current={...defaults,anatomy_height:0,attachment_contour:-3.5,attachment_smoothness:0,shaft_base_width:.98,shaft_mid_width:1.5,shaft_tip_width:1.25,length:1.35,testicle_size:1.4,hang:35,separation:15,z:-11,scale:1.4,width:1.3,depth:1.3,x:0,y:-3.5};
fs.writeFileSync('work/current-fold-fit.json',JSON.stringify({schema:1,asset:'kliff-connected-v04',parameters:current},null,2));
for(const [name,p] of [['neutral',defaults],['current',current],['smooth',{...current,attachment_smoothness:1}]]){
fs.writeFileSync('work/inspection-fit.json',JSON.stringify({schema:1,asset:'kliff-connected-v04',parameters:p}));
await page.locator('#presetfile').setInputFiles('work/inspection-fit.json');await page.locator('#focus').click();
const box=await page.locator('#canvas').boundingBox();await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);await page.mouse.down();await page.mouse.move(box.x+box.width*.5+85,box.y+box.height*.5+15,{steps:20});await page.mouse.up();
await page.waitForTimeout(500);await page.screenshot({path:'work/fold-'+name+'.png'});
}
await browser.close();})();
