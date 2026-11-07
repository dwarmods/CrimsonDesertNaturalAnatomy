"""Read selected current archive entries; honor explicit sparse PAZ IDs in the table."""
from pathlib import Path
import sys,struct,json,hashlib,argparse
from io import BytesIO
parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true');parser.add_argument('--report',default='work/anatomy-current-source-audit.json');args=parser.parse_args()
ROOT=Path(__file__).resolve().parent.parent;sys.path[:0]=[str(ROOT/'work/python-deps'),str(ROOT/'work/CDMW-Full')]
from cdmw.core.archive_format import ArchiveEntry
from cdmw.core.archive_extraction import read_archive_entry_data
from PIL import Image
import numpy as np
folder=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Crimson Desert\0009');pamt=folder/'0.pamt';data=pamt.read_bytes()
_,n,_=struct.unpack_from('<III',data);ids={struct.unpack_from('<III',data,12+i*12)[0] for i in range(n)};off=12+n*12
def sized_bytes():
 global off
 size=struct.unpack_from('<I',data,off)[0];off+=4;block=data[off:off+size];assert len(block)==size;off+=size;return block
class RelativeTrie:
 def __init__(self,block):self.block=block;self.cache={}
 def varint(self,pos):
  value=shift=0
  for _ in range(5):
   b=self.block[pos];pos+=1;value|=(b&127)<<shift
   if b<128:return value,pos
   shift+=7
  raise ValueError('Invalid relative trie integer')
 def get_full_path(self,offset):
  if offset==0xffffffff:return ''
  if offset in self.cache:return self.cache[offset]
  parts=[];seen=set();current=offset
  while current not in self.cache:
   if current in seen or not 0<=current<len(self.block):raise ValueError('Invalid relative trie chain')
   seen.add(current);delta,pos=self.varint(current);length,pos=self.varint(pos);text=self.block[pos:pos+length].decode('utf-8');parts.append((current,text))
   if delta==0:base='';break
   current-=delta
  else:base=self.cache[current]
  for at,text in reversed(parts):base+=text;self.cache[at]=base
  return self.cache[offset]
directories=RelativeTrie(sized_bytes());names=RelativeTrie(sized_bytes())
count=struct.unpack_from('<I',data,off)[0];off+=4
folders=[struct.unpack_from('<IIII',data,off+i*16) for i in range(count)];off+=count*16
ranges=sorted((start,start+size,directories.get_full_path(name).replace('\\','/').strip('/')) for _,name,start,size in folders if size)
count=struct.unpack_from('<I',data,off)[0];off+=4;assert off+count*20<=len(data)
extension_offset=off+count*20;extension_bytes=struct.unpack_from('<I',data,extension_offset)[0]
extensions=data[extension_offset+4:extension_offset+4+extension_bytes].decode('ascii').split('\0')
targets={'character/texture/cd_phm_00_nude_00_0001'+s+'.dds' for s in ('','_n','_sp','_m')}
targets.update(['character/model/1_pc/1_phm/nude/cd_phm_00_nude_00_0001.pac','character/modelproperty/1_pc/1_phm/nude/cd_phm_00_nude_00_0001.pac_xml'])
selected={};cursor=0
aliases={path.replace('/cd_phm_','/phm_'):path for path in targets}
for i in range(count):
 name,paz_offset,compressed,size,paz_id,flags,extension=struct.unpack_from('<IIIIHBB',data,off+i*20)
 assert extension<len(extensions)
 while cursor<len(ranges) and i>=ranges[cursor][1]:cursor+=1
 short=names.get_full_path(name).replace('\\','/').strip('/');directory=ranges[cursor][2] if cursor<len(ranges) and ranges[cursor][0]<=i<ranges[cursor][1] else ''
 path=((directory+'/'+short).strip('/')+extensions[extension]).lower()
 canonical=path if path in targets else aliases.get(path)
 if canonical is None:continue
 assert paz_id in ids and (folder/f'{paz_id}.paz').is_file(),(path,paz_id)
 selected[canonical]=ArchiveEntry(path=path,pamt_path=pamt,paz_file=folder/f'{paz_id}.paz',offset=paz_offset,comp_size=compressed,orig_size=size,flags=flags,paz_index=paz_id)
assert set(selected)==targets,targets-set(selected)
rows=[]
for path,e in selected.items():
 payload,_,note=read_archive_entry_data(e);h=hashlib.sha256(payload).hexdigest();row={'reference_path':path,'current_index_path':e.path,'bytes':len(payload),'sha256':h,'paz_id':e.paz_index}
 if path.endswith('.dds'):
  assert payload[:4]==b'DDS ',path
  im=Image.open(BytesIO(payload));a=np.array(im.resize((128,128)));row.update(size=im.size,mode=im.mode,channel_mean=a.mean((0,1)).tolist())
  if not args.check_only:
   dest=ROOT/'work/kliff-skin'/Path(path).name;dest.write_bytes(payload);im.save(dest.with_suffix('.png'))
 elif path.endswith('.pac'):row['matches_original_geometry_template']=h=='27cd7d4f4b688bf7128e4ef4103c08cab07f410b8f94a8f3ad9b2ed07a65ba7c'
 elif not args.check_only:(ROOT/'work/current-body-property.xml').write_bytes(payload)
 rows.append(row)
report={'paz_record_count':n,'explicit_paz_ids':sorted(ids),'source_index_sha256':hashlib.sha256(data).hexdigest(),'entries':rows,'game_modified':False}
(ROOT/args.report).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
