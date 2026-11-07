"""Inspect the four user-supplied content packages without applying any mod."""
from pathlib import Path,PurePosixPath
import zipfile,subprocess,json,hashlib,collections,re
ROOT=Path(__file__).resolve().parent.parent;SOURCE=(Path.home()/'CrimsonDesertMods')
OUT=ROOT/'outputs/Kliff-Additional-Compatibility-2026-11-06';OUT.mkdir(exist_ok=True)
WORK=ROOT/'work/additional-compatibility-20261106';WORK.mkdir(exist_ok=True)
patterns=[('hide','Hide Underwear Necklace Lantern LanternRings*.rar'),('vaxis','VAXIS*Simulation Physics Mod v.2.4*.zip'),('remove','Nude Character - Remove Character Underwear*.rar'),('enable','Custom Character Underwear Enabled*.rar')]
ours={f['path'].lower() for f in json.loads((ROOT/'outputs/Kliff-Anatomy-Native-0.6.2/Package-Validation.json').read_text())['files']}
packages=[];contents={}
for label,pattern in patterns:
 matches=list(SOURCE.glob(pattern));assert len(matches)==1,matches
 archive=matches[0];dest=WORK/label;dest.mkdir(exist_ok=True)
 if archive.suffix=='.zip':
  with zipfile.ZipFile(archive) as z:
   names=z.namelist()
   for name in names:
    parts=PurePosixPath(name.replace('\\','/'));assert not parts.is_absolute() and '..' not in parts.parts
    if name.endswith('/'):continue
    path=dest.joinpath(*parts.parts);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
 else:
  result=subprocess.run(['tar','-tf',str(archive)],capture_output=True,text=True,check=True);names=result.stdout.splitlines()
  for name in names:
   parts=PurePosixPath(name.replace('\\','/'));assert not parts.is_absolute() and '..' not in parts.parts and not re.match(r'^[a-zA-Z]:',name)
  subprocess.run(['tar','-xf',str(archive),'-C',str(dest)],capture_output=True,text=True,check=True)
 rows=[];documents=[]
 for path in sorted(dest.rglob('*')):
  if not path.is_file():continue
  relative=path.relative_to(dest).as_posix();parts=relative.lower().split('/');runtime='/'.join(parts[parts.index('character'):]) if 'character' in parts else None
  data=path.read_bytes();rows.append({'file':relative,'runtime_path':runtime,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
  if path.name.lower()=='modinfo.json':documents.append({'file':relative,'text':data.decode('utf-8-sig',errors='replace')})
 contents[label]={r['runtime_path']:r for r in rows if r['runtime_path']}
 packages.append({'id':label,'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'file_count':len(rows),'files':rows,'overlaps_with_anatomy_062':sorted(ours&set(contents[label])),'metadata':documents})
overlaps=[]
for i,(a,aa) in enumerate(contents.items()):
 for b,bb in list(contents.items())[i+1:]:
  for p in aa.keys()&bb.keys():overlaps.append({'a':a,'b':b,'path':p,'identical':aa[p]['sha256']==bb[p]['sha256']})
report={'stage':'Static supplied-package inspection; runtime unverified','packages':packages,'direct_overlaps_between_supplied_packages':overlaps,'game_modified':False}
(OUT/'File-Audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'packages':[{k:v for k,v in p.items() if k!='files'} for p in packages],'pairwise_overlaps':overlaps},indent=2))
