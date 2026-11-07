from pathlib import Path
import json,shutil,hashlib,zipfile
ROOT=Path(__file__).resolve().parent;source=ROOT/'neutral-body-rebuild'
OUT=ROOT.parent/'outputs/Kliff-Neutral-Body-v0.3-REVIEW';OUT.mkdir(exist_ok=True)
for a,b in [('Kliff-default-body-review.blend','Kliff-neutral-body-review.blend'),('default-kliff-body-review.png','neutral-body-review.png'),('validation.json','topology-check.json'),('default-body-check.json','default-body-check.json')]:
    shutil.copy2(source/a,OUT/b)
readme='''Kliff neutral anatomy — v0.3 Blender review draft

This is NOT an installable Crimson Desert / DMM mod.
It is not finished, certified seamless, or runtime-physics enabled.

Changes since v0.2
- Replaced the overlapping attachment with a connected triangle bridge into
  the existing lower torso. The attachment has no open/nonmanifold edges.
- Lowered the attachment by 30 mm and increased the prior fit scale by 20%.
  These are draft artistic fitting changes, not a claim of medically ideal size.
- Retained native body skin weights and blended attachment weights into the
  original pelvis. No invented game physics bones are used.
- Added a static preview of Character Creator's default Kliff proportions
  using the game's native affine skinning matrices.
- Matched 7,213 unchanged body vertices to an independently calculated
  default-body reference within 0.0004 mm.

Blender use
Open Kliff-neutral-body-review.blend. The visible body has shape keys Basis
and Default Kliff - native affine preview. The default preview is enabled.
The hands and partial head have corresponding preview shape keys.
The original skeleton is retained for deformation work; the default-proportion
preview is a static shape, not an exact Blender pose-channel reconstruction.
Hidden authoring assets are retained for further work. Source scripts are not
embedded; normal Blender driver and material data remain in the scene.

Outstanding work
- Inspect and refine the skin transition under multiple lighting conditions.
- Bake a game-compatible material with preserved surface detail.
- Check animation, body options, skin settings, clothing masks and LODs.
- Build a validated game archive; perform in-game mounting/visibility checks.
- Establish actual runtime support for ordinary passive anatomy movement.
  Installing TwoReasons does not establish support for this added mesh.

Rights and attribution
Anatomy source: Ultimate Realistic Penis Rig, ThineCrawler.
Source: https://smutba.se/project/8f757313-b08c-41b2-a61f-2105a31d4428/
Source license: Creative Commons Attribution-ShareAlike 4.0 International.
License: https://creativecommons.org/licenses/by-sa/4.0/
Source SHA-256:
ac422bf36d0424384d325bb8e55b1a6f8d6bde798d38a4926eba33a0985e3c13
Adaptations: neutral pose, placement/scale, attachment topology, material
transition and skin weights. Attribution and ShareAlike apply to adaptations
of that licensed source asset.

The scene also contains body/skeleton/texture references extracted from your
local Crimson Desert installation. Those game assets are not relicensed under
Creative Commons. This is a private local review scene, not a redistribution-
cleared mod release. No files from the supplied compatibility mods are embedded.

No game files or DMM imports were changed.
'''
(OUT/'READ-ME.txt').write_text(readme,encoding='utf-8')
checks={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='SHA256.json'}
(OUT/'SHA256.json').write_text(json.dumps(checks,indent=2))
for folder in [OUT,ROOT.parent/'outputs/Kliff-Compatibility-Review']:
    zip_path=folder.parent/(folder.name+'.zip')
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p in sorted(folder.iterdir()):
            if p.is_file():z.write(p,folder.name+'/'+p.name)
    with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
    print(zip_path.name,zip_path.stat().st_size)
status={
 'date':'2026-10-23','scope':'Neutral adult anatomy, Kliff first; no arousal controls',
 'stage':'Connected-body Blender review draft v0.3; unfinished game integration',
 'source_asset_downloaded_and_hash_verified':True,
 'compatibility_archives_checked':['837 Character Creator 9.1.15','3029 Chest and Gloves 2.9.1','3029 Boots and Helmets 2.9.1','3029 Mask 1','3636 TwoReasons 1.0.0'],
 'static_file_conflicts':0,'hotkey_conflict':'F6 shared by Character Creator and TwoReasons; optional F4 INI saved but not installed',
 'topology':json.loads((source/'validation.json').read_text()),
 'default_body_preview':json.loads((source/'default-body-check.json').read_text()),
 'game_modified':False,'runtime_tested':False,'female_work_deferred':True,
 'remaining':['Texture and silhouette review','Game material bake and PAC/LOD integration','Clothing visibility and selection compatibility','Runtime passive physics support and testing']}
(ROOT/'adult-realism-status.json').write_text(json.dumps(status,indent=2))
