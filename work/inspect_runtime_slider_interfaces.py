"""Offline inspection only: inspect exported plugin entry points without calling them."""
from pathlib import Path
import sys,struct,json,hashlib
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'work/python-deps'))
import capstone
p=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Crimson Desert\bin64\BodyPhysics.asi');b=p.read_bytes()
pe=struct.unpack_from('<I',b,60)[0];n=struct.unpack_from('<H',b,pe+6)[0];opt=pe+24;optional=struct.unpack_from('<H',b,pe+20)[0];image=struct.unpack_from('<Q',b,opt+24)[0]
sections=[struct.unpack_from('<8sIIIIIIHHI',b,opt+optional+i*40) for i in range(n)]
def raw(rva):
 for s in sections:
  if s[2]<=rva<s[2]+max(s[1],s[3]):return s[4]+rva-s[2]
 raise ValueError(hex(rva))
exports=json.loads((ROOT/'work/runtime-slider-exports.json').read_text())[0]['exports'];rows=[]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
for e in exports:
 rva=int(e['rva'],16);offset=raw(rva);ins=[]
 for i in md.disasm(b[offset:offset+600],image+rva):
  ins.append(f'{i.address-image:08x} {i.mnemonic:8} {i.op_str}')
  if len(ins)>=90:break
 rows.append({**e,'instructions':ins})
out=ROOT/'outputs/Kliff-Runtime-Development';out.mkdir(exist_ok=True)
(out/'BodyPhysics-Export-Inspection.json').write_text(json.dumps({'sha256':hashlib.sha256(b).hexdigest(),'image_base':hex(image),'exports':rows,'called_exports':False},indent=2))
for row in rows:print(row['name']+'\n'+'\n'.join(row['instructions'])+'\n')
