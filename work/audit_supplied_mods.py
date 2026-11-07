"""Read supplied mod ZIPs; extract only into this task's work directory."""
import sys, json, zipfile, hashlib, collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'python-deps'),str(ROOT/'CDMW-Full')]
from cdmw.core.archive_format import parse_archive_pamt
from cdmw.core.archive_extraction import read_archive_entry_data
SOURCES=(Path.home()/'CrimsonDesertMods')
DEST=ROOT/'compatibility-audit'
DEST.mkdir(exist_ok=True)
patterns=['Female Armor Module - Chest and Gloves 3029*.zip','Female Armor Module - Mask 3029*.zip','Female Armor Module - Boots And Helmets 3029*.zip','Character Creator Enhanced 837 9.1.15*.zip','TwoReasons Sexualized 1.0.0 3636*.zip']
reports=[]
for number,pattern in enumerate(patterns):
    paths=list(SOURCES.glob(pattern)); assert len(paths)==1,paths
    path=paths[0]; unpack=DEST/str(number); unpack.mkdir(exist_ok=True)
    report={'zip':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'files':[],'patches':[],'payloads':[]}
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            target=(unpack/info.filename).resolve()
            assert target.is_relative_to(unpack.resolve()),info.filename
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(info))
            parts=Path(info.filename).parts
            group=next((i for i,p in enumerate(parts) if len(p)==4 and p.isdigit()),None)
            if group is not None and not target.suffix in ('.pamt','.paz','.bin'):
                report['files'].append('/'.join(parts[group+1:]).lower())
            if target.suffix=='.json':
                data=json.loads(target.read_text(encoding='utf-8-sig'))
                for t in data.get('targets',[]):
                    intents=t.get('intents',[])
                    report['patches'].append({'file':t['file'],'count':len(intents),'fields':dict(collections.Counter(i.get('field','') for i in intents)),'intents':intents})
    for pamt in unpack.rglob('*.pamt'):
        for e in parse_archive_pamt(pamt):
            raw,_,note=read_archive_entry_data(e)
            out=(DEST/'decoded'/str(number)/e.path).resolve()
            assert out.is_relative_to((DEST/'decoded'/str(number)).resolve())
            out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
            report['files'].append(e.path.lower())
            report['payloads'].append({'path':e.path,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'note':note})
    if number==4:
        report['plugin_files']=[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in unpack.glob('*') if p.is_file()]
    reports.append(report)
overlaps=[]
for i,a in enumerate(reports):
    for b in reports[i+1:]:
        shared=sorted(set(a['files'])&set(b['files']))
        overlaps.append({'a':a['zip'],'b':b['zip'],'shared_paths':shared})
result={'scope':'Static inspection of supplied files, not in-game compatibility testing','packages':reports,'overlaps':overlaps}
(DEST/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for r in reports:
    print(r['zip']); print('FILES',len(r['files']));print('PATCHES',[(p['file'],p['count'],p['fields']) for p in r['patches']])
    if len(r['files'])<100:print('\n'.join(r['files']))
    print('BODY/PART TABLE',*[p for p in r['files'] if any(k in p for k in ('nude','parttable','meshparam'))],sep='\n')
print('OVERLAPS',json.dumps(overlaps))
