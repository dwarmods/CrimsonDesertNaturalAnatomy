import * as THREE from 'three';

import {OrbitControls} from './vendor/OrbitControls.js';

import {limits,defaults,validate,migrate,deform,fairNormals} from './fit.js';

const $=id=>document.getElementById(id),storageKey='kliff-editor-v11';

document.querySelectorAll('button').forEach(b=>b.disabled=true);

let params=defaults(),history=[{...params}],historyAt=0,asset,session,body,bodyRow,bodyBaseNormals,original,joinPoints,regionFocused=false,exporting=false;

const meshes=[];const status=(s,error=false)=>{$('status').textContent=s;$('status').classList.toggle('error',error);};

const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(36,1,.01,100);camera.up.set(0,0,1);

const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;$('canvas').append(renderer.domElement);

const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.minDistance=.18;controls.maxDistance=8;

scene.add(new THREE.HemisphereLight(0xdce8ef,0x393634,2));

for(const [color,intensity,position] of [[0xffeedb,3,[2,3,4]],[0xcbdfff,2,[-3,-1,2]],[0xffffff,1,[0,-3,3]]]){const light=new THREE.DirectionalLight(color,intensity);light.position.set(...position);scene.add(light);}

const grid=new THREE.GridHelper(3,30,0x536168,0x354249);grid.rotation.x=Math.PI/2;grid.position.z=-.01;grid.material.transparent=true;grid.material.opacity=.35;scene.add(grid);

const resize=()=>{const r=$('canvas').getBoundingClientRect();camera.aspect=r.width/r.height;camera.updateProjectionMatrix();renderer.setSize(r.width,r.height);};new ResizeObserver(resize).observe($('canvas'));

function view(direction='front'){for(const m of meshes)if(m.name.includes('_Hand'))m.visible=!regionFocused;const focus=regionFocused?new THREE.Vector3(asset.pivot[0],asset.pivot[1],asset.pivot[2]-.07):new THREE.Vector3(0,0,.92),distance=regionFocused?1.05:3.3;const dirs={front:[0,1,.1],side:[1,0,.1],back:[0,-1,.1]};camera.position.copy(focus).add(new THREE.Vector3(...dirs[direction]).multiplyScalar(distance));controls.target.copy(focus);controls.update();}

function fitBounds(){const p=body.geometry.attributes.position.array,min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];for(const i of bodyRow.region)for(let a=0;a<3;a++){min[a]=Math.min(min[a],p[i*3+a]);max[a]=Math.max(max[a],p[i*3+a]);}$('measure').textContent=max.map((x,a)=>((x-min[a])*1000).toFixed(1)).join(' × ');}

function update(){if(!body)return;deform(bodyRow.positions,bodyRow.weights,asset.pivot,params,bodyRow,body.geometry.attributes.position.array);body.geometry.attributes.position.needsUpdate=true;body.geometry.computeVertexNormals();const normals=body.geometry.attributes.normal.array;for(let i=0;i<bodyRow.seamNormalWeights.length;i++){const w=bodyRow.seamNormalWeights[i];if(!w)continue;let sum=0;for(let a=0;a<3;a++){const j=i*3+a;normals[j]=normals[j]*(1-w)+(bodyRow.seamNormals[j]+normals[j]-bodyBaseNormals[j])*w;sum+=normals[j]*normals[j];}const inv=1/Math.sqrt(sum);for(let a=0;a<3;a++)normals[i*3+a]*=inv;}fairNormals(normals,bodyRow);body.geometry.attributes.normal.needsUpdate=true;body.geometry.computeBoundingSphere();const points=joinPoints.geometry.attributes.position.array,pos=body.geometry.attributes.position.array;bodyRow.join.forEach((v,i)=>{for(let a=0;a<3;a++)points[3*i+a]=pos[3*v+a];});joinPoints.geometry.attributes.position.needsUpdate=true;joinPoints.geometry.computeBoundingSphere();fitBounds();sync();try{localStorage.setItem(storageKey,JSON.stringify(preset()));}catch{}$('saved').textContent=JSON.stringify(params)===JSON.stringify(defaults())?'Original fit':'Fit autosaved locally';}

function sync(){for(const k of Object.keys(limits)){const scale=['x','y','z','anatomy_height','hang','separation','attachment_contour'].includes(k)?1:100;$('range-'+k).value=params[k]*scale;$('number-'+k).value=Number((params[k]*scale).toFixed(1));}$('undo').disabled=historyAt===0;$('redo').disabled=historyAt===history.length-1;}

function commit(){if(JSON.stringify(history[historyAt])===JSON.stringify(params))return;history=history.slice(0,historyAt+1);history.push({...params});if(history.length>100)history.shift();historyAt=history.length-1;sync();}

function preset(){return {schema:1,asset:'kliff-connected-v04',parameters:{...params}};}

function readPreset(data){if(data.schema!==1||data.asset!=='kliff-connected-v04')throw Error('This preset uses a different body revision. Keep it with editor 1.0; this revision needs a new fit.');return migrate(data.parameters);}

function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);}

const info={anatomy_height:['Anatomy height - relative to pelvis','mm','Moves shaft and testicles only; torso and attachment rim stay fixed. Negative: lower. Positive: higher.'],attachment_smoothness:['Attachment smoothness','%','Smooths the attachment and adjacent fold continuously. Higher values soften more and can reduce local volume.'],attachment_contour:['Attachment contour','mm','Recess or raise the full attachment circumference. Negative: concave. Positive: convex.'],shaft_base_width:['Shaft width - base','%','Side-to-side width at the attachment; blends into the torso.'],shaft_mid_width:['Shaft width - middle','%','Side-to-side width halfway along the shaft.'],shaft_tip_width:['Shaft width - tip','%','Side-to-side width at the end.'],length:['Shaft length','%','Length only; the scrotum keeps its size.'],testicle_size:['Testicle size','%','Volume around the center of each side.'],hang:['Testicle hang','mm','Positive values lower the scrotum.'],separation:['Shaft separation','mm','Positive values move the scrotum farther behind the shaft.'],z:['Pelvis + anatomy height','mm','Moves the fitted anatomy and surrounding pelvis together.'],scale:['Overall anatomy scale','%','Scales the anatomy; the surrounding pelvis keeps its shape.'],width:['Overall width','%',''],depth:['Overall depth','%',''],x:['Left / right','mm',''],y:['Forward / back','mm','']};

for(const [index,[k,[lo,hi]]] of ['anatomy_height','z',...Object.keys(limits).filter(k=>!['anatomy_height','z'].includes(k))].map(k=>[k,limits[k]]).entries()){

 if([0,2,7,11].includes(index)){const h=document.createElement('div');h.className='section-title';h.textContent=({0:'POSITION',2:'ATTACHMENT & SHAFT PROFILE',7:'ANATOMY',11:'OVERALL FIT'})[index];$('controls').append(h);}

 const [label,unit,help]=info[k],factor=unit==='%'?100:1,step=unit==='%'?1:.5,div=document.createElement('div');div.className='control';

 div.innerHTML=`<div class="control-head"><label for="range-${k}">${label}</label><div class="number"><input id="number-${k}" type="number" aria-label="${label} value" min="${lo*factor}" max="${hi*factor}" step="${step}"><span>${unit}</span></div></div><input id="range-${k}" aria-label="${label}" type="range" min="${lo*factor}" max="${hi*factor}" step="${step}">${help?`<small class="control-help">${help}</small>`:''}`;

 $('controls').append(div);$('range-'+k).oninput=e=>{params[k]=Number(e.target.value)/factor;update();};$('range-'+k).onchange=commit;

 $('number-'+k).onchange=e=>{const n=Number(e.target.value);if(e.target.value===''||!Number.isFinite(n)||n<lo*factor||n>hi*factor){status(`Enter ${lo*factor}�${hi*factor} ${unit}.`,true);sync();return;}params[k]=n/factor;update();commit();status('Fit updated.');};

}

$('undo').onclick=()=>{if(historyAt>0){params={...history[--historyAt]};update();}};$('redo').onclick=()=>{if(historyAt<history.length-1){params={...history[++historyAt]};update();}};$('reset').onclick=()=>{params=defaults();update();commit();status('Original fit restored.');};

$('wire').onchange=e=>meshes.forEach(m=>m.material.wireframe=e.target.checked);$('join').onchange=e=>joinPoints.visible=e.target.checked;$('compare').onchange=e=>original.visible=e.target.checked;

document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));$('full').onclick=()=>{regionFocused=false;view();};$('focus').onclick=()=>{regionFocused=true;view();};

$('save').onclick=()=>{download(new Blob([JSON.stringify(preset(),null,2)],{type:'application/json'}),'Kliff-fit.json');status('Preset saved.');};$('load').onclick=()=>$('presetfile').click();$('presetfile').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>16384)throw Error('Preset file is too large.');params=readPreset(JSON.parse(await file.text()));update();commit();status('Preset loaded.');}catch(err){status(err.message,true);}finally{e.target.value='';}};

$('obj').onclick=()=>{let text='# Kliff Body Editor: static geometry, metres, Z up; no rig or textures\n',offset=1;for(const m of meshes){text+='o '+m.name.replace(/[^a-z0-9_-]/gi,'_')+'\n';const p=m.geometry.attributes.position.array;for(let i=0;i<p.length;i+=3)text+=`v ${p[i]} ${p[i+1]} ${p[i+2]}\n`;const ix=m.geometry.index.array;for(let i=0;i<ix.length;i+=3)text+=`f ${ix[i]+offset} ${ix[i+1]+offset} ${ix[i+2]+offset}\n`;offset+=p.length/3;}download(new Blob([text],{type:'text/plain'}),'Kliff-fit-static.obj');status('Static OBJ exported. Use Blender export to retain materials and weights.');};

$('export').onclick=async()=>{if(exporting)return;exporting=true;$('export').disabled=true;try{status('Exporting this fit in Blender…');const r=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json','X-Editor-Token':session.token},body:JSON.stringify(preset())}),reply=await r.json();if(!r.ok)throw Error(reply.error);const deadline=Date.now()+260000;while(Date.now()<deadline){await new Promise(r=>setTimeout(r,1000));const job=await(await fetch('/api/jobs/'+reply.job)).json();if(job.state==='error')throw Error(job.message);if(job.state==='done'){const a=document.createElement('a');a.href=job.url;a.download='';a.click();status('Blender file exported. A copy is saved in the editor’s exports folder.');return;}}throw Error('Export is taking longer than expected. Check the exports folder.');}catch(err){status(err.message,true);}finally{exporting=false;$('export').disabled=!session?.blender;}};

window.addEventListener('keydown',e=>{if(/INPUT/.test(e.target.tagName))return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();$(e.shiftKey?'redo':'undo').click();}});

try{[asset,session]=await Promise.all([fetch('./assets/body.json').then(r=>r.json()),fetch('/api/session').then(r=>r.json())]);for(const row of asset.meshes){const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(row.positions,3));geo.setIndex(row.indices);geo.computeVertexNormals();const mesh=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color:0xc1b6a6,roughness:.82,metalness:0,side:THREE.DoubleSide}));mesh.name=row.name;scene.add(mesh);meshes.push(mesh);if(row.editable){body=mesh;bodyRow=row;bodyBaseNormals=new Float32Array(geo.attributes.normal.array);original=new THREE.Mesh(geo.clone(),new THREE.MeshBasicMaterial({color:0xb9d3ed,wireframe:true,transparent:true,opacity:.24,depthWrite:false}));original.visible=false;scene.add(original);const pg=new THREE.BufferGeometry();pg.setAttribute('position',new THREE.BufferAttribute(new Float32Array(row.join.length*3),3));joinPoints=new THREE.Points(pg,new THREE.PointsMaterial({color:0xbde980,size:.002,sizeAttenuation:true,depthTest:false}));joinPoints.visible=false;joinPoints.renderOrder=10;scene.add(joinPoints);}}let restored=false;try{const stored=localStorage.getItem(storageKey);if(stored){params=readPreset(JSON.parse(stored));restored=true;}}catch{status('An unreadable autosave was ignored.',true);}document.querySelectorAll('button').forEach(b=>b.disabled=false);history=[defaults()];historyAt=0;update();if(restored)commit();view();resize();$('loading').hidden=true;$('export').disabled=!session.blender;status(session.blender?(restored?'Previous fit restored.':'Ready. Changes stay on this computer.'):'Blender not found. Presets and OBJ export are available.');window.editorReady=true;window.editorSnapshot=()=>({parameters:{...params},vertexCount:bodyRow.positions.length/3,firstRegionVertex:Array.from(body.geometry.attributes.position.array.slice(bodyRow.region[0]*3,bodyRow.region[0]*3+3)),historyAt,blender:session.blender});}catch(e){$('loading').textContent='Could not start the editor';status(e.message,true);}

renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
