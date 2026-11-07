# Upload binding probe 0.2

Development diagnostic, not a slider/physics mod. Builds `NeutralRuntimeProbe.asi`.
No installation or game injection is performed by the build scripts.

Offline tests pass for GP/XMM registers, flags, MXCSR, x87 control word, eleven
integer arguments, mixed SSE/stack arguments, return forwarding, and relocation
of a prior E9 detour in a private test process. These tests do not verify the
game's argument semantics, the live BodyPhysics chain, or full game stability.

## Inspected executable profiles

| PE timestamp | Image size | Upload RVA | Evidence |
| --- | --- | --- | --- |
| `0x6aeb7d59` | `0x13cff000` | `0x308f6d0` | Previous 2.04.07 image audit. |
| `0x6aed2e85` | `0x13cc4000` | `0x3090240` | Installed image inspected 2026-11-07; unique matching 56-byte function prefix. No patch version inferred from this match. |

The current image SHA-256 was
`c94ad6c3ea54970a6d2da7a2719753210a7728a91698ed3405dd9125470ed98f`.
The runtime guard uses the profile's timestamp, image size, and function prefix;
it does not hash the whole loaded executable. Unknown fingerprints are refused.
The entry prefix must match, or bytes after offset 16 must match and the entry
must lead to a module named BodyPhysics.asi. Name-based chain recognition is
not proof of compatibility and remains a limitation to review before release.

The worker is intended to start only inside CrimsonDesert.exe. No hook is
installed until **F10** is pressed with the game focused. A capture samples
at most 64 records over 20 seconds. A second press stops sampling. The hook
then remains a pass-through for that launch. Runtime unloading is unsupported.

The observer is intended to restore arguments and preserve original behavior;
it still installs an in-process code hook. It is not an external read-only
recorder. The wrapper does not preserve upper YMM or x87 stack contents and
does not provide complete unwind metadata. No visible body deformation is
implemented by the probe.

Samples include the RDX object's 512-byte header (covering the observed LOD
selector at `+0x19c`), its `+0x70` pointer array / `+0x78` count, rotating entry
samples, and bounded pointer-following at offsets used by the inspected
routine (`+0xa8`, `+0xb8`, and nested `+0x90`). Offsets are observations;
field names, actor identity, and writable deformation ownership are unverified.
Reads use committed-region checks and guarded copies. Failed reads are marked.

Output next to the ASI: `NeutralRuntimeProbe.log` and
`NeutralRuntimeProbe.capture.tsv`. These contain private diagnostic addresses
and bytes. Keep them local; they are excluded by `.gitignore`.
