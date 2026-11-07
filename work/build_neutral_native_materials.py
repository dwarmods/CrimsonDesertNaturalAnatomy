"""Native atlas DDS mip chains and narrowly scoped body material sidecar."""
from pathlib import Path
from io import BytesIO
import json,re,struct,hashlib,xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/Kliff-Anatomy-Native-0.6';FILES=OUT/'files';TEX=FILES/'character/texture/codex'
TEX.mkdir(parents=True,exist_ok=True)
source=ROOT/'outputs/Kliff-Anatomy-Hair-0.5/textures'
specs=[('BaseColor','','kliff_neutral_06'),('Normal','_n','kliff_neutral_06_n'),('PackedMaterial','_sp','kliff_neutral_06_sp'),('SkinMask','_m','kliff_neutral_06_m')]
report=[]
for label,suffix,name in specs:
 image=Image.open(source/(label+'.png')).convert('RGB');size=image.size;is_normal=label=='Normal'
 if is_normal:
  a=np.array(image);a[:,:,1]=255-a[:,:,1];image=Image.fromarray(a)
 header=bytearray((ROOT/'work/kliff-skin'/('cd_phm_00_nude_00_0001'+suffix+'.dds')).read_bytes()[:128])
 fourcc=bytes(header[84:88]);assert fourcc==(b'BC5U' if is_normal else b'DXT1')
 mips=[];level=0
 while True:
  stream=BytesIO();image.save(stream,format='DDS',pixel_format='BC5' if is_normal else 'DXT1');encoded=stream.getvalue();offset=148 if encoded[84:88]==b'DX10' else 128
  payload=encoded[offset:];expected=((image.width+3)//4)*((image.height+3)//4)*(16 if is_normal else 8);assert len(payload)==expected
  mips.append(payload)
  if image.size==(1,1):break
  image=image.resize((max(1,image.width//2),max(1,image.height//2)),Image.Resampling.BOX)
  if is_normal:
   a=np.array(image,dtype=np.float32)/255;xy=a[:,:,:2]*2-1;z=np.sqrt(np.maximum(0,1-(xy*xy).sum(axis=2)));vectors=np.dstack((xy,z));vectors/=np.maximum(1e-8,np.linalg.norm(vectors,axis=2,keepdims=True));a[:,:,:2]=vectors[:,:,:2]*.5+.5;a[:,:,2]=0;image=Image.fromarray(np.uint8(np.clip(a,0,1)*255))
  level+=1
 struct.pack_into('<I',header,8,0xA1007);struct.pack_into('<II',header,12,size[1],size[0]);struct.pack_into('<I',header,20,len(mips[0]));struct.pack_into('<I',header,28,len(mips));struct.pack_into('<I',header,108,0x401008)
 data=bytes(header)+b''.join(mips);path=TEX/(name+'.dds');path.write_bytes(data)
 reopened=Image.open(path);reopened.load();assert reopened.size==size
 report.append({'map':label,'path':path.relative_to(FILES).as_posix(),'size':size,'mips':len(mips),'fourcc':fourcc.decode(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'normal_green_reversed_for_V_down':is_normal})
 print('DDS_READY '+label,flush=True)
original=(ROOT/'work/current-body-property.xml').read_bytes().decode('utf-8')
mapping={'_baseColorTexture':report[0]['path'],'_normalTexture':report[1]['path'],'_materialTexture':report[2]['path'],'_skinDetailMaskTexture':report[3]['path']}
changes=[]
pattern=r'<SkinnedMeshMaterialWrapper\b[^>]*_subMeshName="cd_phm_00_nude_0001"[^>]*>.*?</SkinnedMeshMaterialWrapper>'
def replace_wrapper(match):
 block=match.group();tree=ET.fromstring(block);updated=block
 for p in tree.iter('MaterialParameterTexture'):
  key=p.get('_name')
  if key not in mapping:continue
  child=p.find('ResourceReferencePath_ITexture');assert child is not None
  old=child.get('_path');assert old
  # Match only this texture parameter, preserving all formatting and other parameters.
  pp=r'(<MaterialParameterTexture\b[^>]*_name="'+re.escape(key)+r'"[^>]*>\s*<ResourceReferencePath_ITexture\b[^>]*_path=")[^"]+("[^>]*/>\s*</MaterialParameterTexture>)'
  updated,n=re.subn(pp,lambda m:m.group(1)+mapping[key]+m.group(2),updated);assert n==1
  changes.append({'parameter':key,'old':old,'new':mapping[key]})
 return updated
patched,n=re.subn(pattern,replace_wrapper,original,flags=re.S);assert n>0
before=ET.fromstring('<Root>'+original+'</Root>');after=ET.fromstring('<Root>'+patched+'</Root>')
for a,b in zip(before.iter('SkinnedMeshMaterialWrapper'),after.iter('SkinnedMeshMaterialWrapper')):
 if a.get('_subMeshName')!='cd_phm_00_nude_0001':assert ET.tostring(a)==ET.tostring(b)
relative='character/modelproperty/1_pc/1_phm/nude/phm_00_nude_00_0001.pac_xml';path=FILES/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(patched,encoding='utf-8',newline='')
validation={'stage':'Native DDS and body-only material sidecar candidate; not runtime verified','textures':report,'property_path':relative,'body_material_variants_patched':n,'parameter_changes':changes,'head_and_hand_wrappers_unchanged':True,'original_global_textures_unchanged':True,'common_wrinkle_reference_unchanged':True,'skin_detail_layers_unchanged':True,'normal_convention':'V and bitangent handedness reversed with green-channel inversion to preserve Blender tangent-space direction. Actual game shading remains unverified.','limitations':['Wrinkle driver compatibility with rebuilt body topology unverified.','Original shader flags and skin-detail/damage layers are retained; game hair uses shared skin shader.','No independent runtime physics; clothing/body-picker and other mod compatibility unverified.'],'installed':False}
(OUT/'Native-Material-Validation.json').write_text(json.dumps(validation,indent=2))
print('NATIVE_MATERIALS_READY '+json.dumps({'textures':len(report),'variants':n,'changes':len(changes)}))
