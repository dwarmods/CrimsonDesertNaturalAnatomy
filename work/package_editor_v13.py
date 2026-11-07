from pathlib import Path
p=Path(__file__).with_name('package_body_editor.py');s=p.read_text()
s=s.replace('1.1.0','1.3.0').replace('Editor-1.1.zip','Editor-1.3.zip')
s=s.replace("'controls':['length'", "'controls':['anatomy_height','attachment_contour','attachment_smoothness','shaft_base_width','shaft_mid_width','shaft_tip_width','length'")
s=s.replace("'visual_review':'Reviewed full-body and fitting-region views, including 1365x768 layout'", "'visual_review':'Reviewed actual in-app editor with separate anatomy and pelvis height controls','layout_migration_tests':json.loads((ROOT/'work/editor-v12-tests.json').read_text()),'relative_height_tests':json.loads((ROOT/'work/editor-relative-height-tests.json').read_text())")
exec(compile(s,str(p),'exec'))
