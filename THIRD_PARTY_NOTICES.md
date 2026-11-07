# Attribution and asset boundaries

## Dear ImGui

Subset vendored at `work/neutral-runtime/vendor/imgui`, including the DX11 and
Win32 backends. Version 1.91.5-docking, commit
`368123ab06b2b573d585e52f84cd782c5c006697` from https://github.com/ocornut/imgui.
MIT license; copyright Omar Cornut and Dear ImGui contributors. Full terms are
in that directory's `LICENSE.txt`. The accompanying stb headers preserve their
own notices. No system font files are distributed.

## JSON for Modern C++

Single header vendored at `work/neutral-runtime/vendor/nlohmann/json.hpp`.
Version 3.11.3, commit `9cca280a4d0ccf0c08f47a99aa71d1b0e52f8d03` from
https://github.com/nlohmann/json. MIT license; copyright Niels Lohmann.
Full terms are in `LICENSE.MIT` beside the header.

`work/neutral-runtime/vendor/DEPENDENCIES.json` records original upstream Git
blob IDs for these files. `python work/verify_native_dependencies.py` verifies
the checked-in copies without network access.

## MinHook

Vendored at `work/neutral-runtime/vendor/minhook`. Its BSD-style license,
authors, and bundled HDE notices are preserved in that directory. See
`LICENSE.txt` and source headers for the applicable terms.

## Three.js r180

Vendored at `outputs/Kliff-Body-Editor/web/vendor`, including OrbitControls.
MIT license, copyright its authors. Full terms are in `THREE-LICENSE.txt`.

## Anatomy authoring source (not included)

Ultimate Realistic Penis Rig, by ThineCrawler:
https://smutba.se/project/8f757313-b08c-41b2-a61f-2105a31d4428/

The locally inspected source was distributed under Creative Commons
Attribution-ShareAlike 4.0 International:
https://creativecommons.org/licenses/by-sa/4.0/

Adaptations in the local authoring project include neutral pose, placement,
scale, attachment topology, material transition, skin weights, and interactive
fitting. Attribution and ShareAlike obligations apply to adaptations of that
source asset. This notice does not relicense unrelated code or game assets.

## Game assets and external mods (not included)

Crimson Desert body meshes, skeletons, textures, and other extracted assets
remain subject to their owners' rights. No ownership or redistribution grant
is asserted here. Generated local scenes/packages containing those assets are
excluded from this source repository.

CDMW-Full is an external build dependency. BodyPhysics, Character Creator,
Add Item, underwear/armor/visibility mods, and VAXIS binaries or assets are
not bundled. Compatibility inspection is not redistribution permission or
a guarantee of runtime compatibility.
