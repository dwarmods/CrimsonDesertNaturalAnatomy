"""Build and round-trip a DMM import candidate, with no installed-game writes."""
from pathlib import Path
import sys,json,hashlib,struct,types,zipfile,shutil,time,argparse
parser=argparse.ArgumentParser();parser.add_argument('--version',default='0.6');parser.add_argument('--native-dir',default='outputs/Kliff-Anatomy-Native-0.6');args=parser.parse_args()
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT/'work/CDMW-Full'))
from cdmw.core import archive_overlay as overlay
from cdmw.core.archive_format import parse_archive_pamt,calculate_pa_checksum
from cdmw.core.archive_extraction import read_archive_entry_data
OUT=ROOT/args.native_dir;FILES=OUT/'files'
pac_relative='character/model/1_pc/1_phm/nude/phm_00_nude_00_0001.pac'
pac=FILES/pac_relative;pac.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OUT/'Kliff-Neutral-Body-Hair.pac',pac)
payloads={p.relative_to(FILES).as_posix():p.read_bytes() for p in FILES.rglob('*') if p.is_file()}
assert len(payloads)==6
material=json.loads((OUT/'Native-Material-Validation.json').read_text())
geometry=json.loads((OUT/'Native-Geometry-Validation.json').read_text())
assert geometry['sha256']==hashlib.sha256(pac.read_bytes()).hexdigest()
assert all(l['collapsed_triangles_after_position_quantization']==0 for l in geometry['lods'])
assert all(l['lost_positive_bone_influences']==0 for l in geometry['lods'])
assert material['head_and_hand_wrappers_unchanged']
for row in material['textures']:assert hashlib.sha256(payloads[row['path']]).hexdigest()==row['sha256']
PACKAGE=ROOT/('outputs/Kliff-Neutral-Anatomy-'+args.version+'-DMM-TEST');group=PACKAGE/'0036';group.mkdir(parents=True,exist_ok=True)
# DMM input follows the fixed-parent/no-extension-table format used by the
# user's supplied compiled mods. It is deliberately not a rewrite of current
# game indexes. The native checksum accelerator is absent, so use its Python
# reference implementation for this workspace package only.
environment=dict(overlay.build_overlay_archive.__globals__)
environment['_payload_checksum']=lambda payload,stop_event=None:calculate_pa_checksum(payload)
build=types.FunctionType(overlay.build_overlay_archive.__code__,environment,'build_reference_overlay',overlay.build_overlay_archive.__defaults__,overlay.build_overlay_archive.__closure__)
build.__kwdefaults__=overlay.build_overlay_archive.__kwdefaults__
print('BUILDING_DMM_OVERLAY '+str(sum(map(len,payloads.values())))+' bytes',flush=True)
archive=build([overlay.OverlayFile(p,d,len(d),0) for p,d in sorted(payloads.items())])
(group/'0.pamt').write_bytes(archive.pamt_bytes);(group/'0.paz').write_bytes(archive.paz_bytes)
entries=parse_archive_pamt(group/'0.pamt');assert {e.path for e in entries}==set(payloads)
for e in entries:
 data,_,_=read_archive_entry_data(e);assert data==payloads[e.path]
assert calculate_pa_checksum(archive.pamt_bytes[12:])==archive.pamt_checksum
assert struct.unpack_from('<I',archive.pamt_bytes,16)[0]==calculate_pa_checksum(archive.paz_bytes)
info={'name':'Kliff Neutral Anatomy with Hair - TEST','version':'0.6.0-test','author':'Local authoring prototype','description':'Offline-built body and rooted pubic hair test candidate. Replaces base male nude body and its body-only material sidecar; four unique atlas DDS textures. No runtime physics. Not in-game verified. Import only after reading INSTALL.txt.'}
if args.version!='0.6':info.update(version=args.version+'-test',name='Kliff Neutral Anatomy with Hair '+args.version+' - TEST',description='DDS mip-block header metadata corrected; encoded textures and geometry unchanged from v0.6. Compatibility with Add Item remains unverified. Offline-built test candidate; read INSTALL.txt.')
(PACKAGE/'modinfo.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
instructions='''KLIFF NEUTRAL ANATOMY WITH HAIR 0.6 - DMM TEST CANDIDATE
30 October 2026

This is the first native body+hair+atlas candidate from the revised Blender
model. It has been checked offline, not tested in Crimson Desert. It is not
the completed realism mod. Do not install while the game is running.

LATER TEST
1. Save and fully exit the game when convenient.
2. Disable any earlier Kliff neutral-body/anatomy replacement in DMM.
3. Import this ZIP into DMM. Enable the single Kliff Neutral Anatomy with Hair
   - TEST entry and use the manager's Mount/Apply operation.
4. After DMM succeeds, launch the game and inspect an unclothed adult Kliff.
   With the supplied Character Creator Enhanced version, the base human body
   is the existing body-picker index 1. The default Kliff variation is index 0.
   The package replaces the underlying base male nude mesh; it adds no new
   body-picker choice and has not been verified with those runtime options.
5. Check the neutral pose, walking, crouching, the attachment edge, texture
   alignment, shading, and whether the hair remains attached during movement.
   Then check trousers/underwear visibility and distance changes. Check for
   exposed anatomy through clothing before using it beyond a short test.
6. To remove, exit the game, disable this entry in DMM and Mount/Apply again.

The 0036 directory is an import archive, following the same package structure
as the supplied DMM content mods. DMM manages registration/remapping; do not
manually copy it over an existing game archive. No meta/0.papgt, skeleton,
plugin, executable, save, or manager configuration is supplied or changed.
The package contains only its modinfo.json, INSTALL.txt and two archive files.

CONTENTS AND OFFLINE CHECKS
- One rebuilt body PAC, with rooted hair and a single shared atlas material.
- One model-property sidecar: 24 texture references changed across six body
  variants; head and hand wrappers remain unchanged.
- Four unique 4096x4096 DDS maps with complete mip chains: base color, BC5
  tangent normal, packed material RGB and skin mask. Global original textures
  are not replaced, so other clothing meshes keep their original texture UVs.
- All four native body LODs reparse with 59,233 vertices and 100,081 triangles.
  Head/hand raw records and faces are retained. Positive skin influences are
  retained. Native position/weight quantization yields up to 0.623 mm static
  default-variation preview error. 649 collapsed triangles were removed.
- Atlas tangent lanes and handedness are authored from the new UVs. UV V and
  normal-map green are converted together from Blender to native convention.
- All six archive entries were read back byte-for-byte and checksums verified.

REMAINING LIMITS
Actual mounting, rendering, skin colors, Character Creator body variations,
clothing hide rules and compatibility with the supplied armor/physics mods
remain unverified. This replaces the base male body and can affect other
characters sharing that mesh. Disable other replacements of the same PAC or
material sidecar during an initial test. Existing Character Creator and Female
Armor Module configuration files are not replaced.

The source mesh's skin flags, cloth-guide donor state, skin-detail layers,
damage maps and common wrinkle reference are retained. Their behavior on the
rebuilt topology is unverified. Hair uses the body skin shader; it is static
geometry with inherited skeletal weights, not independent hair simulation.
The FIT bones remain Blender authoring controls; no extra game bones or
runtime anatomy physics are implemented. All four body LODs currently repeat
full geometry, so distant performance is not optimized. The attachment lip
still needs geometric refinement; hair disguises part of it.

ATTRIBUTION
Anatomy source: Ultimate Realistic Penis Rig, ThineCrawler.
https://smutba.se/project/8f757313-b08c-41b2-a61f-2105a31d4428/
Adaptation license: Creative Commons Attribution-ShareAlike 4.0.
https://creativecommons.org/licenses/by-sa/4.0/
Changes include neutral fitting, connected topology, smoothing, authoring
controls, an atlas, pubic hair and native-format conversion. Local game body,
skeleton and texture references retain their original ownership; this does
not grant redistribution rights to those game assets. Local test package.
Native format construction uses the existing local CDMW tooling.
'''
if args.version!='0.6':
 instructions=instructions.replace('0.6 - DMM TEST CANDIDATE',args.version+' - DMM TEST CANDIDATE').replace('30 October 2026','6 November 2026')
 instructions='''V0.6.2 CORRECTION AND COMPATIBILITY STATUS
The four atlas DDS headers now carry the correct first-four-mip byte sizes for
4096x4096 textures. v0.6 had retained the smaller source textures' sizes in
engine-specific reserved words. Encoded pixels, geometry and material paths
are unchanged. This fixes a demonstrated metadata inconsistency; its effect
on the startup failure has NOT been established in game.

User testing found an interaction: Diagnostic A crashes with the old Add Item
plugin loaded and launches without it. Diagnostic B (no added textures) launches.
The crash module/logs identify Add Item 1.3.4 targeting game 2.04.04. The user's
supplied ZIP contains a different binary, Add Item 1.3.13 targeting game 2.04.07;
all its supplied file hashes were verified. That newer plugin has not been
installed or tested by this build. Do not patch or disable unrelated plugins
on the assumption that the DDS correction proves the interaction is resolved.

For a controlled next check, update Add Item through DMM using the supplied
1.3.13 archive, preserving your chosen INI, then test Diagnostic A unchanged.
If A reaches the title screen, replace A with this v0.6.2 candidate for a
separate body/material test. Keep v0.6 and all diagnostics disabled while
v0.6.2 is enabled. Make manager changes only with the game closed.
No third-party ASI or default INI is bundled into this anatomy ZIP.

'''+instructions
(PACKAGE/'INSTALL.txt').write_text(instructions,encoding='utf-8')
zip_path=ROOT/('outputs/Kliff-Neutral-Anatomy-'+args.version+'-DMM-TEST.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(PACKAGE.rglob('*')):
  if p.is_file():z.write(p,PACKAGE.name+'/'+p.relative_to(PACKAGE).as_posix())
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None and len(z.namelist())==4
 assert [n for n in z.namelist() if n.endswith('.json')]==[PACKAGE.name+'/modinfo.json']
report={'stage':'DMM import archive candidate validated offline; mount and runtime unverified','package':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),'files':[{'path':p,'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for p,d in sorted(payloads.items())],'archive_entry_byte_roundtrip':True,'archive_checksums_verified':True,'zip_crc_verified':True,'DMM_import_format':'Same fixed-parent index structure as supplied DMM compiled content mods; not imported or mounted in this session.','game_modified':False,'installed':False,'in_game_tested':False,'runtime_physics':False}
(OUT/'Package-Validation.json').write_text(json.dumps(report,indent=2))
shutil.copy2(PACKAGE/'INSTALL.txt',OUT/'README.txt')
print('DMM_TEST_PACKAGE_READY '+json.dumps({k:v for k,v in report.items() if k!='files'}),flush=True)
