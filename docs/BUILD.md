# Build and authoring notes

Keep the `work/` and `outputs/` directory layout: most authoring scripts resolve
their workspace root from their own location. They write development outputs
in this checkout. They do not constitute a clean-room asset generator.

## Native development

Requirements: Windows x64, Visual Studio 2022 C++ tools, Windows SDK, MASM,
and CMake 3.20 or newer. MinHook source and its license are included.

```powershell
cmake -S work/neutral-runtime -B work/neutral-runtime/build -G "Visual Studio 17 2022" -A x64
cmake --build work/neutral-runtime/build --config Release
ctest --test-dir work/neutral-runtime/build -C Release --output-on-failure
```

The current configuration includes the fitting backend, background control
worker, motion core, experimental observer, and offline tests. The combined
Release build and its tests pass locally. These are offline development checks,
not a verified live game release process.
No build/install step should copy an ASI into a live game automatically.

The native build also contains the Dear ImGui panel, preset component,
interaction tests, and a software D3D11 PNG preview executable. Dear ImGui
and JSON for Modern C++ are vendored at pinned commits; configuring this
build does not fetch them. Verify their source hashes with:

```powershell
python work/verify_native_dependencies.py
```

The panel is an offline-tested component. It has not been connected to an
in-game renderer/input host. Load/save buttons emit action requests for the
future host; they do not open file dialogs or alter game files by themselves.

## Standalone editor

Requirements: Python 3, a browser, and Blender for `.blend` exports. The local
HTTP server uses Python's standard library. NumPy is used in Blender fitting.
Three.js r180 is vendored under its MIT license.

Restore locally owned/generated assets at:

- `outputs/Kliff-Body-Editor/web/assets/body.json`
- `outputs/Kliff-Body-Editor/body-template.blend`

Then launch:

```powershell
python outputs/Kliff-Body-Editor/editor.py
```

It serves `127.0.0.1:48763`. The repository alone lacks the body assets needed
for a functioning preview/export. The editor exports a fitting scene, not a
live game patch. Its historic `READ-ME.txt` describes that editor revision.

## Native asset pipeline

Additional dependencies: NumPy, Pillow with BC5/DXT1 DDS support, LZ4, Blender,
and [CDMW-Full](https://github.com/Ratty123/CDMW-Full) checked out separately
at `work/CDMW-Full`. Scripts use private CDMW internals; upstream changes may
require adaptation. CDMW itself is not vendored here.

Local inputs include the licensed anatomy source scene, extracted game PAC/PAB
and body textures, deformation fields/body JSON, fitted scenes, and atlas maps.
Those inputs must be obtained/generated locally. Inspect each script's input
paths before running it. The historical fitting/smoothing scripts depend on
specific intermediate meshes and object names; a fresh clone is not enough
to regenerate every intermediate automatically.

The latest export path uses:

1. `export_neutral_hair_native.py` to collect body/hair geometry and native bind data from the authoring scene.
2. `build_native_anatomy_pac.py` to create and validate the PAC against the original game skeleton and preserved submeshes.
3. `build_neutral_native_materials.py` to encode atlas DDS files and a body material sidecar into the v0.6 staging directory.
4. **`fix_neutral_dds_block_metadata.py`** to correct engine-specific mip sizes and produce v0.6.2 staging. Do not skip this step when using the historical material builder.
5. `package_neutral_native_dmm.py --version 0.6.2 --native-dir outputs/Kliff-Anatomy-Native-0.6.2` to build and round-trip the local DMM archive.

The geometry builder's defaults target an earlier candidate. For the hair
package, specify `--input work/anatomy-hair-native-input.json`, the matching
native staging directory, and `--name Kliff-Neutral-Body-Hair.pac` explicitly.
Packaging requires the geometry/material validation reports produced by the
previous steps. Packaging success proves archive consistency, not in-game
visibility, motion, or compatibility.

Browser verification scripts require Node.js and `playwright`. Mesh-based
editor tests also need the excluded local body assets. Historical compatibility
audits expect supplied mod archives in `~/CrimsonDesertMods`.
