const {chromium}=require('playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:320,height:870}});
 await page.goto('http://127.0.0.1:48763/');await page.waitForFunction(()=>window.editorReady);
 const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,panel:document.querySelector('aside').getBoundingClientRect().toJSON()}));
 if(layout.scrollWidth>layout.width||layout.panel.right>layout.width)throw Error('Narrow panel overflow');
 const old=JSON.parse(fs.readFileSync('work/editor-test-preset.json'));
 for(const k of ['anatomy_height','attachment_contour','attachment_smoothness','shaft_base_width','shaft_mid_width','shaft_tip_width'])delete old.parameters[k];
 fs.writeFileSync('work/editor-v11-migration-preset.json',JSON.stringify(old));
 await page.locator('#presetfile').setInputFiles('work/editor-v11-migration-preset.json');
 await page.waitForFunction(()=>window.editorSnapshot().parameters.z===-15);
 const migrated=await page.evaluate(()=>window.editorSnapshot().parameters);
 if(migrated.attachment_smoothness!==0||migrated.shaft_mid_width!==1||migrated.attachment_contour!==0||migrated.testicle_size!==1.1)throw Error('Preset migration lost values');
 const session=await(await page.request.get('http://127.0.0.1:48763/api/session')).json();
 const checks=[];
 for(const [name,parameters,token,asset] of [
  ['missing_session',migrated,'','kliff-connected-v04'],
  ['wrong_asset',migrated,session.token,'wrong'],
  ['invalid_contour',{...migrated,attachment_contour:999},session.token,'kliff-connected-v04'],
  ['invalid_smoothness',{...migrated,attachment_smoothness:-1},session.token,'kliff-connected-v04'],
  ['invalid_width',{...migrated,shaft_tip_width:0},session.token,'kliff-connected-v04'],
  ['missing_control',old.parameters,session.token,'kliff-connected-v04']]){
   const res=await page.request.post('http://127.0.0.1:48763/api/export',{headers:{'X-Editor-Token':token},data:{schema:1,asset,parameters}});
   if(res.status()!==(name==='missing_session'?403:400))throw Error(name+' status '+res.status());checks.push(name);
 }
 fs.writeFileSync('work/editor-api-tests.json',JSON.stringify({passed:true,checks},null,2));
 fs.writeFileSync('work/editor-v12-tests.json',JSON.stringify({passed:true,version:session.version,narrow_layout:layout,legacy_preset_migration:true},null,2));
 await browser.close();console.log('V12_LAYOUT_MIGRATION_API_PASSED');
})().catch(e=>{console.error(e);process.exit(1)});
