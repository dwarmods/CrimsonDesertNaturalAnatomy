# Crimson Desert Natural Anatomy

Development sources for a neutral adult Kliff body replacement, fitting editor,
surface-rooted pubic hair, and experimental passive motion support.

**This repository is a source snapshot, not a finished in-game physics or slider mod.**
The current game target is Crimson Desert **2.04.07**.

## Current state

| Component | Evidence and limits |
| --- | --- |
| Static body and hair package, v0.6.2 | User reported that the local DMM test package works. This does not verify every animation, appearance option, or mod combination. |
| Standalone editor, v1.5 | Source for length, width profile, placement, attachment contour/smoothing, testicle size, hang, and separation. Local mesh/template assets are required. Its preview predates the latest hair/material package. |
| Blender fitting rig | Authoring controls exist; they are not new native game bones. |
| Passive motion solver | Previous solver-only build passed offline numerical tests. Not connected to visible game geometry. |
| Upload-path observer | Experimental source and ABI tests written; the combined build and live behavior remain unverified. |
| In-game sliders and naked physics | **Unfinished.** Requires verified actor, geometry/pose, visibility, and render-update bindings. |

The intended movement is passive gravity, damping, and response to character
movement. Clothed characters should use the original body behavior. No arousal
controls are part of this project.

## Source layout

- `work/neutral-runtime/`: C++ motion core, tests, and an experimental x64 upload observer with vendored MinHook.
- `outputs/Kliff-Body-Editor/`: standalone Python server, shared deformation math, browser UI, and Blender export code.
- `work/*.py`, `work/*.cjs`: authoring, fitting, smoothing, material, native PAC, packaging, and verification scripts. Earlier revision scripts are retained as development history; they are not one automatic build sequence.
- `presets/neutral-fit.json`: saved neutral fitting parameters.
- `docs/`: build prerequisites, runtime limitations, and third-party attribution.

Game meshes, textures, skeletons, generated Blender scenes, captured memory,
private logs, compiled third-party plugins, and local DMM packages are excluded.
The local v0.6.2 test package is not included in this source publication.

See [build notes](docs/BUILD.md), [runtime status](docs/RUNTIME.md), and
[attribution](THIRD_PARTY_NOTICES.md). No general license has yet been selected
for project-authored code; the included third-party components retain their own licenses.
