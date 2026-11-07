import sys, pickle, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python-deps'),str(ROOT/'CDMW-Full')]
from cdmw.core.archive_extraction import read_archive_entry_data
from PIL import Image
entries=pickle.loads((ROOT/'entries.pkl').read_bytes())
paths=['character/texture/'+name+'.dds' for name in (
    'cd_phm_00_nude_00_0001','cd_phm_00_nude_00_0001_n',
    'cd_phm_00_nude_00_0001_hand','cd_phm_00_head_00_0001_01')]
out=ROOT/'kliff-skin';out.mkdir(exist_ok=True)
report=[]
for path in paths:
    matches=[e for e in entries if e.path.lower()==path]
    if not matches: raise RuntimeError(path)
    entry=matches[-1]
    data,_,note=read_archive_entry_data(entry)
    dest=out/Path(path).name;dest.write_bytes(data)
    with Image.open(dest) as im:
        im.convert('RGB').save(dest.with_suffix('.png'))
        report.append(dict(path=path,group=entry.package_label,sha256=hashlib.sha256(data).hexdigest(),size=im.size))
(out/'sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
