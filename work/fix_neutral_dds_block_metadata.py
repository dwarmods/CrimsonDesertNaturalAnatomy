"""Correct stale engine mip-block sizes while preserving encoded pixels and mesh."""
from pathlib import Path
import json,struct,hashlib,shutil,sys
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'work/CDMW-Full'))
from cdmw.core.pathc_format import validate_dds_payload,block_infos_for
OLD=ROOT/'outputs/Kliff-Anatomy-Native-0.6';OUT=ROOT/'outputs/Kliff-Anatomy-Native-0.6.2';OUT.mkdir(exist_ok=True)
shutil.copy2(OLD/'Kliff-Neutral-Body-Hair.pac',OUT/'Kliff-Neutral-Body-Hair.pac')
shutil.copy2(OLD/'Native-Geometry-Validation.json',OUT/'Native-Geometry-Validation.json')
rows=[]
for source in (OLD/'files').rglob('*'):
 if not source.is_file():continue
 relative=source.relative_to(OLD/'files');path=OUT/'files'/relative;path.parent.mkdir(parents=True,exist_ok=True)
 before=source.read_bytes();data=before
 if source.suffix.lower()=='.dds':
  desc=validate_dds_payload(before);wanted=block_infos_for(before);old_words=list(struct.unpack_from('<11I',before,32))
  result=bytearray(before);result[32:76]=wanted+bytes(28);data=bytes(result)
  assert data[:32]==before[:32] and data[76:]==before[76:]
  assert tuple(struct.unpack_from('<4I',data,32))==desc.mip_bytes[:4]
  validate_dds_payload(data)
  rows.append({'path':relative.as_posix(),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(data).hexdigest(),'old_first_four_block_sizes':old_words[:4],'new_first_four_block_sizes':list(desc.mip_bytes[:4]),'encoded_pixel_payload_unchanged':True,'only_reserved_header_bytes_changed':True})
 path.write_bytes(data)
assert len(rows)==4
material=json.loads((OLD/'Native-Material-Validation.json').read_text())
for texture in material['textures']:
 match=next(r for r in rows if r['path']==texture['path']);texture['sha256']=match['after_sha256'];texture['engine_block_size_metadata_matches_actual_mips']=True
material['correction']='The v0.6 atlas dimensions changed to 4096, but source first-four-mip byte sizes remained in DDS reserved header words. v0.6.2 corrects those sizes without changing encoded pixels.'
material['compatibility']='User confirmed Diagnostic A crashes with old Add Item loaded and launches without it; B launches with Add Item. Supplied Add Item 1.3.13 is a different binary targeting game 2.04.07. Neither updated-plugin compatibility nor this header correction has been tested in game.'
(OUT/'Native-Material-Validation.json').write_text(json.dumps(material,indent=2))
report={'stage':'DDS engine block metadata corrected offline; runtime effect unverified','changed_textures':rows,'geometry_unchanged':True,'material_paths_and_parameters_unchanged':True,'game_modified':False,'in_game_tested':False}
(OUT/'DDS-Header-Correction.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
