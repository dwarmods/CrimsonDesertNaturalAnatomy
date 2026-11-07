import runpy,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ctx=runpy.run_path(str(ROOT/'prepare_kliff.py'))
from cdmw.modding.skeleton_variation_parser import parse_pabc_skeleton_variation,apply_skeleton_variation_to_mesh,_bone_bind_matrix,_neutral_variation_bind_matrix,_skin_matrices
mesh,rig,palette=ctx['mesh'],ctx['rig'],ctx['palette']
reports=[]
for name in ['cd_phm_00_nude_01_0002','cd_phm_00_nude_00_0001']:
    path=ROOT/'extracted/0009/character/binary/skeletonvariation/1_pc/1_phm/nude'/f'{name}.pabc'
    variation=parse_pabc_skeleton_variation(path.read_bytes(),str(path),skeleton=rig)
    clone=apply_skeleton_variation_to_mesh(mesh,rig,palette,variation)
    payload=json.loads((ROOT/'kliff-body.json').read_text())
    for p,sm in zip(payload['parts'],clone.submeshes):p['vertices']=sm.vertices
    payload['variation']=name
    matrices=[_bone_bind_matrix(b) for b in rig.bones]
    for record in variation.records:
        if record.bone_index>=0:matrices[record.bone_index]=_neutral_variation_bind_matrix(matrices[record.bone_index],record.matrix_blocks[0])
    payload['target_bone_matrices']=matrices
    payload['skinning_matrices']=_skin_matrices(rig.bones,matrices)
    (ROOT/f'kliff-body-{name}.json').write_text(json.dumps(payload))
    displacement=[math.dist(a,b) for a,b in zip(mesh.submeshes[2].vertices,clone.submeshes[2].vertices)]
    reports.append({'variation':name,'records':variation.record_count,'matched':variation.matched_record_count,'max_body_displacement_m':max(displacement),'mean_body_displacement_m':sum(displacement)/len(displacement)})
(ROOT/'kliff-variation-report.json').write_text(json.dumps(reports,indent=2))
print(json.dumps(reports,indent=2))
