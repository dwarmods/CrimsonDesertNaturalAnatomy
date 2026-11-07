from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent.parent
APP=ROOT/'outputs/Kliff-Body-Editor'
p=APP/'web/app.js';s=p.read_text()
s=s.replace("z:['Penis placement - higher / lower','mm','Positive values raise the fitted region.']", "z:['Pelvis placement - up / down','mm','Moves the shaft and testicles together. Negative: lower. Positive: higher.']")
s=s.replace('Object.entries(limits).entries()', "['z',...Object.keys(limits).filter(k=>k!=='z')].map(k=>[k,limits[k]]).entries()")
s=s.replace("if([0,5,10].includes(index)){const h=document.createElement('div');h.className='section-title';h.textContent=index===0?'ATTACHMENT & SHAFT PROFILE':index===5?'ANATOMY & PLACEMENT':'OVERALL FIT';$('controls').append(h);}", "if([0,1,6,10].includes(index)){const h=document.createElement('div');h.className='section-title';h.textContent=({0:'PELVIS PLACEMENT',1:'ATTACHMENT & SHAFT PROFILE',6:'ANATOMY',10:'OVERALL FIT'})[index];$('controls').append(h);}")
p.write_text(s)
p=APP/'READ-ME.txt';s=p.read_text().replace('- Vertical placement of the fitted anatomy.', '- Pelvis placement - up / down, at the top: moves the shaft and testicles\n  together from -40 to +40 mm; negative is lower, positive is higher.');p.write_text(s)
# Check the existing position parameter translates every fitted vertex equally.
sys.path.insert(0,str(APP));from fit import deform,LIMITS
a=json.loads((APP/'web/assets/body.json').read_text());r=next(m for m in a['meshes'] if m['editable'])
params={k:v[2] for k,v in LIMITS.items()};params['z']=20
result=deform(r['positions'],r['weights'],a['pivot'],params,r)
error=max(abs(result[i*3+2]-r['positions'][i*3+2]-.02) for i in r['region'])
assert error<1e-12,error
assert all(result[i*3:i*3+2]==r['positions'][i*3:i*3+2] for i in r['region'])
print(json.dumps({'whole_region_translation_verified':True,'vertices':len(r['region']),'max_error_metres':error}))
