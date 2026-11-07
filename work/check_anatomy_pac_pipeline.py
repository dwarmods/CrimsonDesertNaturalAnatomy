"""Offline PAC export probe; never writes to the game or mod manager.

Checks an unchanged rebuild and a single face subdivision on Kliff's body.
This is a format capability test, not evidence of in-game compatibility.
"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'python-deps'), str(ROOT / 'CDMW-Full')]
from cdmw.modding.mesh_parser import parse_pac
from cdmw.modding.mesh_pac_builder import build_pac

source = ROOT / 'extracted/0009/character/model/1_pc/1_phm/nude/cd_phm_00_nude_00_0001.pac'
raw = source.read_bytes()
original = parse_pac(raw, str(source))
report = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'game_modified': False,
          'runtime_tested': False, 'tests': {}}

def compare_geometry(expected, actual):
    assert len(expected.submeshes) == len(actual.submeshes)
    maximum = 0.0
    for a, b in zip(expected.submeshes, actual.submeshes):
        assert a.name == b.name
        assert len(a.vertices) == len(b.vertices)
        assert [tuple(f) for f in a.faces] == [tuple(f) for f in b.faces]
        maximum = max(maximum, max(math.dist(x, y) for x, y in zip(a.vertices, b.vertices)))
    assert maximum < 0.0002, maximum
    return maximum

rebuilt = build_pac(original, raw)
report['tests']['unchanged'] = {
    'byte_identical': rebuilt == raw,
    'max_position_error_m': compare_geometry(original, parse_pac(rebuilt, 'unchanged.pac')),
    'bytes': len(rebuilt),
}

modified = copy.deepcopy(original)
body = next(sm for sm in modified.submeshes if sm.name == 'CD_PHM_00_Nude_0001')
a, b, c = body.faces[0]
idx = len(body.vertices)
body.vertices = list(body.vertices) + [tuple(sum(body.vertices[k][axis] for k in (a, b, c)) / 3 for axis in range(3))]
body.uvs = list(body.uvs) + [tuple(sum(body.uvs[k][axis] for k in (a, b, c)) / 3 for axis in range(2))]
normal = [sum(body.normals[k][axis] for k in (a, b, c)) / 3 for axis in range(3)]
length = math.sqrt(sum(x*x for x in normal))
body.normals = list(body.normals) + [tuple(x / length for x in normal)]
# The test's extra vertex inherits a known valid row; it is not an anatomical weight transfer.
body.bone_indices = list(body.bone_indices) + [body.bone_indices[a]]
body.bone_weights = list(body.bone_weights) + [body.bone_weights[a]]
body.faces = [(a,b,idx),(b,c,idx),(c,a,idx)] + list(body.faces[1:])
body.source_vertex_map = list(range(idx)) + [a]
body.source_vertex_map_authority = 'target_donor_record'
body.source_vertex_offsets = list(body.source_vertex_offsets) + [body.source_vertex_offsets[a]]
try:
    altered = build_pac(modified, raw)
    decoded = parse_pac(altered, 'subdivision-probe.pac')
    report['tests']['added_geometry'] = {
        'passed': True, 'added_vertices': 1, 'added_faces': 2,
        'max_position_error_m': compare_geometry(modified, decoded), 'bytes': len(altered),
    }
except Exception as exc:
    report['tests']['added_geometry'] = {'passed': False, 'error': str(exc)}

(ROOT / 'anatomy-pac-pipeline-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
