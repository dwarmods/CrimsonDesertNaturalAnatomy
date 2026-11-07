import bpy,json
from pathlib import Path
APP=Path(__file__).resolve().parent.parent/'outputs/Kliff-Body-Editor'
bpy.ops.wm.open_mainfile(filepath=str(APP/'body-template.blend'),load_ui=False,use_scripts=False)
a=json.loads((APP/'web/assets/body.json').read_text());r=next(m for m in a['meshes'] if m['editable']);ob=bpy.data.objects[r['name']]
for i,v in enumerate(ob.data.vertices):
 co=r['positions'][3*i:3*i+3];v.co=co;ob.data.shape_keys.key_blocks['Basis'].data[i].co=co
ob.data.update();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(APP/'body-template.blend'))
