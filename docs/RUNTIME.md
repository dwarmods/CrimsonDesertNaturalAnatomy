# Runtime evidence and remaining work

The motion core is independent of the game. It uses Y-up coordinates, a fixed
simulation step, anchored nodes, spring/damping forces, segment constraints,
offset limits, capsule exclusion, and resets after teleports or long frames.
Clothed/unknown visibility suppresses simulation when the caller supplies that
state. The game does not yet supply this state to the solver.

The combined native build passed tests for fixed roots, constraints,
frame-rate parity, stability, clothing gating, resets, simple capsule exclusion,
and invalid input rejection. Those checks establish numerical behavior only;
they do not establish calibrated anatomical realism or live motion.

The static PAC retains the original game skeleton. The added `FIT` bones in
Blender are authoring controls, not native game physics bones. No live anatomy
deformation binding has been verified.

The experimental `NeutralRuntimeProbe` source targets inspected upload entries
for two executable fingerprints, guarded by PE timestamp, image size, and entry bytes.
F10 is intended to install an observer and collect bounded samples. It restores
arguments before forwarding the call and is intended not to change pose or
mesh values. Installing a hook still changes executable routing, so it is
not an external read-only tool. **It builds and passes offline ABI tests;
live behavior remains unverified.** It does not implement sliders or physics.

The assembly wrapper is intended to preserve GP/XMM arguments, flags, MXCSR,
and the x87 control word. It does not preserve upper YMM state or arbitrary
x87 stack state. Its ABI test suite passes offline. Existing-hook chaining
and module identification need further review before use alongside plugins.
Captured addresses/bytes are local diagnostics and must not be committed.

Still required before a working runtime release:

1. Review exception/unload behavior and verify coexistence with actual existing hooks; offline ABI tests already pass.
2. Verify upload argument semantics, actor ownership, buffer lifetime, and the relationship to rendered Kliff geometry.
3. Establish a supported deformation path and bind the solver's outputs to it.
4. Verify naked/clothed visibility and restore original behavior when clothes are worn.
5. Connect validated in-game slider UI to bounded fitting parameters and persistent settings.
6. Validate movement, camera distance/LODs, save loading, and compatibility in the actual game.

Matching exported function names or signatures is not proof of a safe API or
visible deformation. Existing BodyPhysics geometry exports were inspected
offline, but no usable source/SDK was available and their setter semantics
were not established. No guessed exports have been called.

The native fitting backend now matches the standalone editor on all 36 local
full-mesh reference cases. Its background control worker produces CPU geometry
snapshots with revision guards. Those are not live applied mesh revisions. See
[SLIDERS.md](SLIDERS.md) for measurements and integration requirements.

Public Character Creator source was subsequently found online. Its documented
body sliders edit skeleton-variation bones and refresh the character; this
does not establish arbitrary deformation support for this added mesh. Reference:
https://github.com/Khione95/Crimson-Desert-Character-Creator/blob/main/CharacterCreator/CharacterCreator/faceshape.h
No Character Creator source has been copied into this project.
