from pathlib import Path
import json,hashlib,configparser,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
AUDIT=ROOT/'compatibility-audit'
OUT=ROOT.parent/'outputs/Kliff-Compatibility-Review';OUT.mkdir(exist_ok=True)
r=json.loads((AUDIT/'report.json').read_text())
cc=AUDIT/'3/Character Creator/Character Creator Enhanced/0009/character/descriptors/customizationmeta/meshparam_example_kliff.xml'
body=ET.fromstring(cc.read_text(encoding='utf-8')).find("ParamDesc[@Index='0']")
r['kliff_body_options']=[{'index':s.attrib['Index'],'prefab':s.find('MeshList').attrib['MeshFileName'],'skeleton_variation':s.attrib.get('SkeletonVariation')} for s in body.findall('MeshSet')]
r['conditional_groups']=[]
for i in range(3):
    for p in (AUDIT/'decoded'/str(i)).rglob('conditionalpartprefab*.xml'):
        x=ET.fromstring('<Root>'+p.read_text(encoding='utf-8-sig')+'</Root>')
        r['conditional_groups'].append({'file':p.name,'conditions':len(x.findall('Condition')),'groups':[{'name':g.attrib['Name'],'body_prefabs':[a.attrib['Name'] for a in g.findall('PartPrefab')]} for g in x.findall('PartPrefabGroup')]})
patches=[]
for package in r['packages']:
    for patch in package['patches']:
        for intent in patch['intents']:
            patches.append((package['zip'],patch['file'],intent.get('key'),intent.get('field'),intent.get('new')))
conflicts=[]
for i,a in enumerate(patches):
    for b in patches[i+1:]:
        if a[0]!=b[0] and a[1:4]==b[1:4] and a[4]!=b[4]:conflicts.append({'a':a,'b':b})
r['different_values_for_same_explicit_patch_key']=conflicts
src=AUDIT/'4/BodyPhysics.ini'
raw=src.read_bytes();needle=b'ActivationKeyVK=117'
assert raw.count(needle)==1
patched=raw.replace(needle,b'ActivationKeyVK=115')
(OUT/'BodyPhysics-F4.ini').write_bytes(patched)
a=configparser.ConfigParser();b=configparser.ConfigParser();a.read_string(raw.decode('utf-8-sig'));b.read_string(patched.decode('utf-8-sig'))
diff=[(s,k,a[s][k],b[s][k]) for s in a.sections() for k in a[s] if a[s][k]!=b[s][k]]
assert diff==[('General','activationkeyvk','117','115')],diff
r['optional_config_change']={'source_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(patched).hexdigest(),'differences':diff,'applied_to_game':False}
game=Path(r'C:\Program Files (x86)\Steam\steamapps\common\Crimson Desert\bin64')
r['installed_plugin_hash_match']={}
for name,source in [('BodyPhysics.asi',AUDIT/'4/BodyPhysics.asi'),('BodyPhysics.ini',src),('CharacterCreator.asi',AUDIT/'3/Character Creator/CharacterCreator.asi')]:
    live=game/name
    r['installed_plugin_hash_match'][name]=live.exists() and hashlib.sha256(live.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
r['runtime_tested']=False
(OUT/'static-audit.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
body_lines='\n'.join(f"  {b['index']}: {b['prefab']}" for b in r['kliff_body_options'])
text=f'''Compatibility review — supplied packages — 23 October 2026

This is a static file inspection. It does not certify in-game compatibility,
visibility, clothing masking, skin-colour sliders, or runtime physics.

Supplied packages
- Character Creator Enhanced (Nexus 837), archive 9.1.15.
- Female Armor Module Chest and Gloves (Nexus 3029), archive 2.9.1.
- Female Armor Module Boots and Helmets (Nexus 3029), archive 2.9.1.
- Female Armor Module Mask (Nexus 3029), archive 1.
- TwoReasons (Nexus 3636), supplied 1.0.0 preset.

Confirmed from the files
- No overlapping replacement asset paths among the supplied content packages.
- Conflicting values for identical explicit JSON patch keys: {len(conflicts)}.
- Female Armor Module selects armor replacements through female body-prefab
  groups. None of its three packages supplies a replacement male body PAC.
- Character Creator changes appearance/customization definitions and provides
  an Equip All Armor item eligibility patch. Its body picker has
  {len(r['kliff_body_options'])} entries. Index 0 is Kliff's default; index 1 is
  the base human body used by the earlier fitting scene. Body shape changes
  include skeleton-variation changes, so one preview cannot prove every fit.
- The supplied TwoReasons archive contains only BodyPhysics.asi and its INI.
  Its menu defaults to F6, colliding with Character Creator's Kliff menu.
- The INI describes bone-based deformation and measured body contacts. It
  explicitly excludes world-object contacts and does not establish support
  for added anatomy or arbitrary custom skeleton bones.

Optional hotkey correction
BodyPhysics-F4.ini is the supplied INI with exactly one setting changed:
  [General] ActivationKeyVK: 117 (F6) -> 115 (F4)
All physics settings remain identical. This is a reviewable local copy, not an
installed change. To use it later: close the game, back up the active
BodyPhysics.ini, then apply ActivationKeyVK=115 through DMM's ASI configuration.
If installing the file manually, name it BodyPhysics.ini in bin64. Keep the
manager's configuration consistent so a later Apply does not restore F6.
F4 has not been checked against every other plugin you may have installed.

Integration requirements for the revised neutral Kliff body
- Preserve Character Creator's existing body selection indices and prefab IDs.
- Check the default Kliff skeleton variation and the base-human option.
- Do not overwrite Female Armor Module's conditional armor rules.
- Preserve native body weights and clothing hide regions; test underwear,
  equipped trousers, transmog, body changes, skin sliders, and distance LODs.
- Do not assume BodyPhysics animates new geometry or add a competing physics
  owner to the same bones. Runtime support remains unverified.
- Character Creator's README warns against combining its separately downloaded
  Female Armor Fit with Female Armor Module. Female Armor Fit was not among
  these supplied archives; this is not a blanket conflict with Character Creator.

No game files, mod-manager imports, or live plugin settings were changed.
The anatomy model remains an unfinished Blender prototype.

Character Creator body options (zero-based indices)
{body_lines}
'''
(OUT/'READ-ME.txt').write_text(text,encoding='utf-8')
print(json.dumps({'patch_conflicts':len(conflicts),'body_options':len(r['kliff_body_options']),'installed_hash_match':r['installed_plugin_hash_match'],'config_diff':diff},indent=2))
