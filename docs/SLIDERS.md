# Native slider backend

The C++ backend now implements the standalone editor's 16 fitting controls,
including the attachment loft, weighted relaxation, and metric smoothing.
It operates on the editor's Z-up mesh in metres. It is not yet connected to
the game renderer, and it does not replace skinning, normals/tangents, or
the passive motion solver.

`control_specs()` provides keys, labels, ranges, and defaults. Unsupported
values, nonfinite inputs, malformed fields/topology, and asymmetric metric
patches are rejected before a fit is used. `Fitter` is immutable and may be
shared by worker sessions.

`ControlSession` handles revision-checked edits on any caller thread. A worker
coalesces dragging, calculates fitted positions, and publishes immutable CPU
snapshots only for the current revision. Old solves cannot overwrite newer
settings. Heavy geometry work is not performed by `edit()` or `snapshot()`.
`staged_revision` means **CPU geometry prepared**, not applied to the game.
If changes arrive continuously, publication waits for a quiet interval and a
solve that has not been superseded. Render interpolation remains future work.

## Local parity check

Local game-derived assets are intentionally excluded from Git. With your
existing editor body asset and NumPy available:

```powershell
python work/build_native_fit_fixtures.py --asset <local-body.json> --out work/neutral-runtime/build/local-fit-fixtures
cmake -S work/neutral-runtime -B work/neutral-runtime/build -DNEUTRAL_FIT_FIXTURES:PATH=<absolute-fixture-directory>
cmake --build work/neutral-runtime/build --config Release
ctest --test-dir work/neutral-runtime/build -C Release --output-on-failure
```

The fixture exporter writes `NAFIT01!` little-endian binary data, including
positions, fields, topology, and smoothing coefficients, plus full Python
reference results. The reader bounds file size, counts, and adjacency sizes;
constructing `Fitter` validates semantic constraints. Do not publish those
fixtures: they contain local body geometry.

Verification on 2026-11-07: all 36 cases (neutral, each slider at both limits,
saved fit, all-minimum and all-maximum combinations), 27,161 vertices, maximum
native/Python position difference **1.76528165e-14 m**. One local release run
averaged **50.042 ms** per solve; this is not an in-game frame-rate measurement.
Additional tests cover regional isolation, relative height, invalid inputs,
stale edits, immutable output snapshots, and 200 coalesced drag updates.

## Live integration still required

1. Identify the added anatomy body's actual render buffers and their lifetime.
2. Map authoring vertex IDs through the split native mesh and bind-space transforms.
3. Submit positions and regenerated normals/tangents through a verified update path.
4. Respect actor ownership, body variation, naked visibility, animation, and LODs.
5. Connect a rendered in-game menu to `ControlSession`, and acknowledge an applied
   revision only after the actual body uses that geometry.

The current build has no in-game menu and changes no game body geometry.
