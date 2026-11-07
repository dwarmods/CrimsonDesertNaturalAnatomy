from pathlib import Path
import json,hashlib,zipfile,shutil
ROOT=Path(__file__).resolve().parent.parent
APP=ROOT/'outputs/Kliff-Body-Editor'
report={'editor_version':'1.1.0','date':'2026-10-24','browser_tests':json.loads((ROOT/'work/editor-browser-tests.json').read_text()),'blender_reopen_test':json.loads((ROOT/'work/editor-export-verification.json').read_text()),'api_validation':json.loads((ROOT/'work/editor-api-tests.json').read_text()),'duplicate_launch':'Verified second launch reuses existing editor without binding a second server','visual_review':'Reviewed full-body and fitting-region views, including 1365x768 layout','control_independence':json.loads((ROOT/'work/editor-control-tests.json').read_text()),'anatomy_repair':json.loads((ROOT/'work/editor-anatomy-repair.json').read_text()),'game_modified':False,'runtime_physics_implemented':False,'game_export_implemented':False}
(APP/'VALIDATION.json').write_text(json.dumps(report,indent=2))
files=[p for p in APP.rglob('*') if p.is_file() and 'exports' not in p.relative_to(APP).parts and '__pycache__' not in p.relative_to(APP).parts and p.name!='SHA256.json' and p.suffix!='.blend1']
checks={p.relative_to(APP).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(APP/'SHA256.json').write_text(json.dumps(checks,indent=2));files.append(APP/'SHA256.json')
package=ROOT/'outputs/Kliff-Body-Editor-1.1.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for p in sorted(files):z.write(p,'Kliff-Body-Editor/'+p.relative_to(APP).as_posix())
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    for name,digest in checks.items():assert hashlib.sha256(z.read('Kliff-Body-Editor/'+name)).hexdigest()==digest
(ROOT/'work/editor-status.json').write_text(json.dumps({'status':'Separate local fitting editor implemented and tested','version':'1.1.0','package':str(package),'live_url':'http://127.0.0.1:48763/','controls':['length','testicle_size','hang','separation','z','scale','width','depth','x','y'],'exports':['JSON preset','static OBJ','Blender scene'],'source_model':'Connected-body v0.4 draft','game_integration':'Not implemented'},indent=2))
print(json.dumps({'package':str(package),'files':len(files),'bytes':package.stat().st_size,'sha256':hashlib.sha256(package.read_bytes()).hexdigest()},indent=2))
