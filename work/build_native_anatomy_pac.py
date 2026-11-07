"""Offline neutral anatomy PAC candidate. No game skeleton extension or deployment."""
from pathlib import Path
import sys,json,copy,types,struct,hashlib,math,collections
import numpy as np
import argparse
args_parser=argparse.ArgumentParser()
args_parser.add_argument('--input',default='work/anatomy-pac-native-input.json')
args_parser.add_argument('--output',default='outputs/Kliff-Anatomy-Authoring-0.4')
args_parser.add_argument('--name',default='Kliff-Neutral-Anatomy-GEOMETRY-CANDIDATE.pac')
args=args_parser.parse_args()
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'work/CDMW-Full'))
from cdmw.modding import mesh_pac_builder as writer
from cdmw.modding.mesh_parser import parse_pac,resolve_pac_bone_palette,_parse_par_sections,_find_pac_descriptors,_validated_pac_descriptor_prefix,_parse_pac_geometry_section
from cdmw.modding.skeleton_parser import parse_pab
OUT=ROOT/args.output;OUT.mkdir(parents=True,exist_ok=True)
source=ROOT/'work/extracted/0009/character/model/1_pc/1_phm/nude/cd_phm_00_nude_00_0001.pac';raw=source.read_bytes()
payload=json.loads((ROOT/args.input).read_text());row=payload['row'];slot=payload['palette_reuse_slot']
rig=parse_pab((source.parent.parent/'phm_01.pab').read_bytes(),'phm_01.pab');palette=resolve_pac_bone_palette(raw,rig)
assert hashlib.sha256(raw).hexdigest()==payload['source_sha256'] and len(palette)==189
hashes=[rig.bones[i].name_hash for i in palette];needle=struct.pack('<H',len(hashes))+struct.pack('<'+'I'*len(hashes),*hashes)
assert raw.count(needle)==1;palette_offset=raw.index(needle)
original=parse_pac(raw,str(source));ss=_parse_par_sections(raw);by={s['index']:s for s in ss};s0=by[0];lod_count=raw[s0['offset']+4];desc=_validated_pac_descriptor_prefix(_find_pac_descriptors(raw,s0['offset'],s0['size'],lod_count),ss)
# Re-prove that the chosen slot is unused by every output skin row, including preserved LODs.
for lod in range(lod_count):
 m=_parse_pac_geometry_section(raw,str(source),desc,by[lod_count-lod],lod)
 for part in m.submeshes[:2]:
  assert all(not any(i==slot and w>0 for i,w in zip(ids,ws)) for ids,ws in zip(part.bone_indices,part.bone_weights))
pelvis=next(i for i,b in enumerate(rig.bones) if b.name=='Bip01 Pelvis')
expected_palette=list(palette);expected_palette[slot]=pelvis
patched=bytearray(raw);offset=palette_offset+2+slot*4;struct.pack_into('<I',patched,offset,rig.bones[pelvis].name_hash);patched=bytes(patched)
assert len(patched)==len(raw) and raw[:offset]==patched[:offset] and raw[offset+4:]==patched[offset+4:]
assert resolve_pac_bone_palette(patched,rig)==tuple(expected_palette)
working=copy.deepcopy(original);body=working.submeshes[2]
for key in ('vertices','normals','uvs','faces','bone_indices','bone_weights'):setattr(body,key,[tuple(v) for v in row[key]])
body.source_vertex_map=list(row['source_donors']);body.source_vertex_map_authority='target_donor_record';body.vertex_count=len(body.vertices);body.face_count=len(body.faces)
def full_lods(sm,desc,count):
 result=[]
 for _ in range(count):
  variant=copy.copy(sm);variant.source_vertex_map=list(range(len(sm.vertices)));result.append(variant)
 return result
environment=dict(writer._build_pac_full_rebuild.__globals__);environment['_pac_lod_variants_for_submesh']=full_lods
build=types.FunctionType(writer._build_pac_full_rebuild.__code__,environment,'build_neutral_anatomy',writer._build_pac_full_rebuild.__defaults__,writer._build_pac_full_rebuild.__closure__);build.__kwdefaults__=writer._build_pac_full_rebuild.__kwdefaults__
data=build(original,working,patched,preserve_runtime_abi=True,preserve_original_submesh_indices=(0,1))
removed_quantized_triangles=0
if 'tangents' in row:
 section_probe=_parse_par_sections(data);probe_by={s['index']:s for s in section_probe};probe0=probe_by[0]
 probe_desc=_validated_pac_descriptor_prefix(_find_pac_descriptors(data,probe0['offset'],probe0['size'],lod_count),section_probe)
 probe=_parse_pac_geometry_section(data,'quantized probe',probe_desc,probe_by[lod_count],0).submeshes[2]
 probe_tri=np.array(probe.vertices)[np.array(probe.faces)]
 area=np.linalg.norm(np.cross(probe_tri[:,1]-probe_tri[:,0],probe_tri[:,2]-probe_tri[:,0]),axis=1)*.5
 keep=area>=1e-16;removed_quantized_triangles=int(np.sum(~keep))
 if removed_quantized_triangles:
  body.faces=[f for f,k in zip(body.faces,keep) if k];body.face_count=len(body.faces)
  data=build(original,working,patched,preserve_runtime_abi=True,preserve_original_submesh_indices=(0,1))
# Atlas UVs require newly authored tangent lanes rather than donor tangents.
if 'tangents' in row:
 sections=_parse_par_sections(data);by_new={s['index']:s for s in sections};s0_new=by_new[0]
 desc_new=_validated_pac_descriptor_prefix(_find_pac_descriptors(data,s0_new['offset'],s0_new['size'],lod_count),sections)
 result=bytearray(data)
 for lod in range(lod_count):
  sm=_parse_pac_geometry_section(data,'atlas',desc_new,by_new[lod_count-lod],lod).submeshes[2]
  for vi,at in enumerate(sm.source_vertex_offsets):
   tx,ty,tz=row['tangents'][vi]
   lane=max(1,min(32767,round((tx+1)*.5*32767)))
   if tz<0:lane=-lane
   struct.pack_into('<h',result,at+6,lane)
   packed=struct.unpack_from('<I',result,at+16)[0]&~(1023|0x80000000)
   packed|=max(0,min(1023,round((ty+1)*.5*1023)))
   if row['tangent_signs'][vi]<0:packed|=0x80000000
   struct.pack_into('<I',result,at+16,packed)
 data=bytes(result)
path=OUT/args.name;path.write_bytes(data)
assert resolve_pac_bone_palette(data,rig)==tuple(expected_palette)
sections=_parse_par_sections(data);by={s['index']:s for s in sections};s0=by[0];desc=_validated_pac_descriptor_prefix(_find_pac_descriptors(data,s0['offset'],s0['size'],lod_count),sections)
variation=json.loads((ROOT/'work/kliff-body-cd_phm_00_nude_01_0002.json').read_text());C=np.array(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)),dtype=float)
matrices=[C@np.array(m).reshape(4,4).T@np.linalg.inv(C) for m in variation['skinning_matrices']]
expected_points=np.array(row['vertices']);expected_points=np.column_stack((expected_points[:,0],-expected_points[:,2],expected_points[:,1],np.ones(len(expected_points))))
preview=np.zeros((len(expected_points),3))
for vi,(slots,ws) in enumerate(zip(row['bone_indices'],row['bone_weights'])):
 for bi,w in zip(slots,ws):preview[vi]+=(matrices[expected_palette[bi]]@expected_points[vi])[:3]*w
reports=[]
for lod in range(lod_count):
 m=_parse_pac_geometry_section(data,path.name,desc,by[lod_count-lod],lod);out=next(p for p in m.submeshes if p.name==body.name)
 assert out.faces==body.faces and len(out.vertices)==len(body.vertices)
 position_error=max(math.dist(a,b) for a,b in zip(out.vertices,body.vertices));skin_error=0.;posed=np.zeros_like(preview)
 for vi,(ids,ws,expected_ids,expected_ws) in enumerate(zip(out.bone_indices,out.bone_weights,body.bone_indices,body.bone_weights)):
  actual={i:w for i,w in zip(ids,ws) if w>0};expected=dict(zip(expected_ids,expected_ws));assert set(actual)==set(expected)
  skin_error=max(skin_error,sum(abs(actual[i]-expected[i]) for i in expected))
  v=out.vertices[vi];point=np.array((v[0],-v[2],v[1],1))
  for bi,w in actual.items():posed[vi]+=(matrices[expected_palette[bi]]@point)[:3]*w
 posed_error=float(np.max(np.linalg.norm(posed-preview,axis=1)))
 assert position_error<.0001 and posed_error<.002
 original_lod=_parse_pac_geometry_section(raw,str(source),_validated_pac_descriptor_prefix(_find_pac_descriptors(raw,ss[0]['offset'],ss[0]['size'],lod_count),ss),{s['index']:s for s in ss}[lod_count-lod],lod)
 for before,after in zip(original_lod.submeshes[:2],m.submeshes[:2]):
  assert before.faces==after.faces
  assert [raw[o:o+40] for o in before.source_vertex_offsets]==[data[o:o+40] for o in after.source_vertex_offsets]
 uv_error=float(np.max(np.abs(np.array(out.uvs)-np.array(row['uvs']))));assert uv_error<.0005
 tangent_metrics={}
 if 'tangents' in row:
  ts=[];ns=[];signs=[]
  for at in out.source_vertex_offsets:
   packed=struct.unpack_from('<I',data,at+16)[0];lane=struct.unpack_from('<h',data,at+6)[0]
   tx=abs(lane)/32767*2-1;ty=(packed&1023)/1023*2-1;tz=math.sqrt(max(0,1-tx*tx-ty*ty))*(-1 if lane<0 else 1)
   ts.append((tx,ty,tz));signs.append(-1 if packed&0x80000000 else 1)
  ts=np.array(ts);ns=np.array(out.normals)
  tangent_error=float(np.max(np.linalg.norm(ts-np.array(row['tangents']),axis=1)))
  assert tangent_error<.08 and signs==row['tangent_signs'],(tangent_error,[(i,signs[i],row['tangent_signs'][i]) for i in range(len(signs)) if signs[i]!=row['tangent_signs'][i]][:5],row['tangents'][int(np.argmax(np.linalg.norm(ts-np.array(row['tangents']),axis=1)))])
  tangent_metrics={'maximum_tangent_vector_error':tangent_error,'maximum_abs_normal_dot_tangent':float(np.max(np.abs(np.sum(ts*ns,axis=1)))),'all_handedness_signs_preserved':True}
 points=np.array(out.vertices);triangles=points[np.array(out.faces)];areas=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)*.5
 reports.append({'lod':lod,'body_vertices':len(out.vertices),'body_triangles':len(out.faces),'maximum_bind_position_error_m':position_error,'maximum_skin_L1_error':skin_error,'lost_positive_bone_influences':0,'maximum_native_affine_preview_error_m':posed_error,'head_and_hands_raw_records_and_faces_preserved':True,'maximum_UV_error':uv_error,'collapsed_triangles_after_position_quantization':int(np.sum(areas<1e-16)),**tangent_metrics})
report={'stage':'Native geometry candidate only; materials, clothing visibility and runtime behavior unverified','file':path.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_sha256':payload['source_sha256'],'palette_binding':{'count_unchanged':len(palette),'reused_unused_slot':slot,'old_name':rig.bones[palette[slot]].name,'new_name':rig.bones[pelvis].name,'existing_game_skeleton_bone':True,'skeleton_file_modified':False,'metadata_hash_entry_changed_bytes':4,'all_preserved_head_hand_LODs_verified_slot_unused':True,'candidate_palette_resolves_against_original_PAB':True,'runtime_binding_verified':False},'lods':reports,'material_limit':payload['material_limit'],'opaque_record_donor_maximum_distance_m':payload['maximum_opaque_record_donor_distance_m'],'authoring_controls_in_game':False,'runtime_physics':False,'installed':False,'game_assets_modified':False}
report.update(removed_triangles_collapsed_by_position_quantization=removed_quantized_triangles,UV_conversion=payload.get('UV_conversion'),source_objects=payload.get('objects'),fallback_tangent_corners=payload.get('fallback_tangent_corners',0))
(OUT/'Native-Geometry-Validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
