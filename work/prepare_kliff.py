"""Read-only body extraction into an intermediate Blender input."""
import sys, json, hashlib
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE/'CDMW-Full'))
from cdmw.modding.mesh_parser import parse_pac, resolve_pac_bone_palette
from cdmw.modding.skeleton_parser import parse_pab

root = BASE/'extracted/0009/character/model/1_pc/1_phm'
p = root/'nude/cd_phm_00_nude_00_0001.pac'
s = root/'phm_01.pab'
mesh = parse_pac(p.read_bytes(), str(p))
rig = parse_pab(s.read_bytes(), str(s))
palette = resolve_pac_bone_palette(p.read_bytes(), rig)
parts = []
for sm in mesh.submeshes:
    parts.append(dict(name=sm.name, vertices=sm.vertices, faces=sm.faces,
                      uvs=sm.uvs, bone_indices=sm.bone_indices, bone_weights=sm.bone_weights))
bones = [dict(index=b.index, name=b.name, parent=b.parent_index, matrix=b.bind_matrix)
         for b in rig.bones]
payload = dict(source=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
               skeleton_sha256=hashlib.sha256(s.read_bytes()).hexdigest(),
               parts=parts, bones=bones, palette=palette)
(BASE/'kliff-body.json').write_text(json.dumps(payload), encoding='utf-8')
for p in parts:
    bounds = [(min(v[a] for v in p['vertices']), max(v[a] for v in p['vertices'])) for a in range(3)]
    print(p['name'], len(p['vertices']), len(p['faces']), bounds)
print('Skeleton',rig.parser_mode, 'bones',len(bones),'palette',len(palette))
for b in bones:
    if any(w in b['name'].lower() for w in ['pelvis','hip','thigh','genital','penis']):
        print(b)
