"""Package the offline authoring deliverable; never write to the installed game."""
from pathlib import Path
import json, shutil, hashlib, zipfile
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/Kliff-Anatomy-Hair-0.5'
readme='''KLIFF NEUTRAL ANATOMY WITH PUBIC HAIR - AUTHORING REVIEW 0.5
30 October 2026

Open Kliff-Neutral-Anatomy-With-Hair.blend in Blender 5.2 or newer. All five
atlas images are packed into the Blender file; external PNG copies are also
included. Pubic-Hair-Review.png is a Blender render, not an in-game screenshot.
This ZIP is a Blender authoring package, not a DMM-installable game mod.

HAIR
1,550 tapered surface-rooted strands cover the pubic attachment area, with
extra density along the seam and a softer distribution above it. Strand
lengths vary from 14 to 28 mm. The separate object is named:
  Pubic hair - surface rooted neutral groom
Use the Outliner eye/render icons to hide or show the hair. The underlying
body geometry is unchanged; hair masks part of the seam and does not repair
the remaining raised lip. No independent hair simulation is included.

FITTING CONTROLS
The file opens with the authoring rig active in Pose Mode. Select a bone and
use G, R or S; Alt-G, Alt-R and Alt-S reset its transform.
  FIT anatomy root: move the anatomy relative to the anchored pelvis.
  FIT shaft base/middle/distal: adjust neutral curvature.
  FIT scrotum left/right: fit the scrotal regions separately.
  FIT pelvis anchor: locked to hold the body.
Hair vertices inherit both original game weights and fitting weights from
their surface donor, so the groom follows the local fitting controls. Large
edits can distort the body transition. These controls are authoring bones;
they have not been added to the installed game skeleton. The existing web
editor has not been changed by this package. Saved-Fit.json records the fit
used before the authoring controls are adjusted.

VERIFICATION AND LIMITS
The saved Blender file was reopened. Body coordinates, polygon connectivity
and all body weights match the hairless atlas source exactly. Every hair
vertex was checked against its root donor's native and fitting weights.
A 10 mm root-control move gives identical hair/donor translation. The five
atlas images are packed. Combined UV/normal-split geometry is 59,218 vertices,
within a 16-bit mesh index limit; this is a capacity check, not a working PAC.
Hair-Validation.json contains the measurements. The hair has 27,900 vertices
and 46,500 triangles, and is not optimized for distant LODs.

No game files were changed and this version has not been tested in the game.
Native material binding, hair shader behavior, texture mip behavior, clothing
visibility, Character Creator/other mod compatibility and runtime physics
remain unverified. The shared skin material approximates the hair appearance.
The portable normal bake approximates vector displacement; native normal Y
convention is unverified. Packed material channels are preserved from the
local body source without assigning them guessed roughness/specular meanings.
Hair is not a substitute for refining the underlying attachment geometry.

ATTRIBUTION
Anatomy source: Ultimate Realistic Penis Rig, ThineCrawler.
https://smutba.se/project/8f757313-b08c-41b2-a61f-2105a31d4428/
Source adaptation license: Creative Commons Attribution-ShareAlike 4.0.
https://creativecommons.org/licenses/by-sa/4.0/
Changes: neutral fitting, connected topology, smoothing, authoring controls,
single-material atlas and procedurally generated neutral pubic hair.
Local Crimson Desert body/skeleton/texture references retain their original
ownership and are not relicensed by this package. Local authoring review only.
'''
(OUT/'README.txt').write_text(readme,encoding='utf-8')
shutil.copy2(ROOT/'outputs/Kliff-Anatomy-Authoring-0.4/Saved-Fit.json',OUT/'Saved-Fit.json')
material=json.loads((ROOT/'outputs/Kliff-Anatomy-Materials-0.5/Material-Validation.json').read_text())
for row in material['maps']:
 if 'covered_pixels' in row:row['opaque_alpha_pixels']=row.pop('covered_pixels')
 for suffix in ('min','max'):
  if 'covered_RGB_'+suffix in row:row['all_image_RGB_'+suffix]=row.pop('covered_RGB_'+suffix)
material['alpha_count_note']='Opaque alpha is not a measurement of occupied UV coverage.'
material['limitations']=[s for s in material['limitations'] if 'packed material/mask textures and current mod-manager archive mapping' not in s]
material['limitations'].append('Packed RGB maps have since been remapped from verified current source archives; actual native material binding and game normal convention remain unverified.')
(OUT/'Material-Validation.json').write_text(json.dumps(material,indent=2))
shutil.copy2(ROOT/'outputs/Kliff-Anatomy-Materials-0.5/Native-Support-Maps.json',OUT/'Native-Support-Maps.json')
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='Manifest.json'}
(OUT/'Manifest.json').write_text(json.dumps(manifest,indent=2))
zip_path=ROOT/'outputs/Kliff-Anatomy-0.5-Pubic-Hair-REVIEW.zip'
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(OUT.rglob('*')):
  if p.is_file():z.write(p,arcname='Kliff-Anatomy-Hair-0.5/'+p.relative_to(OUT).as_posix())
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
report={'file':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),'zip_crc_verified':True,'files':len(manifest)+1,'game_modified':False,'in_game_tested':False}
(ROOT/'outputs/Kliff-Anatomy-0.5-Pubic-Hair-Package.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
