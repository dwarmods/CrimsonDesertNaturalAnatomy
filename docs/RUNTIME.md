# Runtime evidence and remaining work

The motion core is independent of the game. It uses Y-up coordinates, a fixed
simulation step, anchored nodes, spring/damping forces, segment constraints,
offset limits, capsule exclusion, and resets after teleports or long frames.
Clothed/unknown visibility suppresses simulation when the caller supplies that
state. The game does not yet supply this state to the solver.

The previous solver-only executable passed tests for fixed roots, constraints,
frame-rate parity, stability, clothing gating, resets, simple capsule exclusion,
and invalid input rejection. Those checks establish numerical behavior only;
they do not establish calibrated anatomical realism or live motion.

The static PAC retains the original game skeleton. The added `FIT` bones in
Blender are authoring controls, not native game physics bones. No live anatomy
deformation binding has been verified.

The experimental `NeutralRuntimeProbe` source targets an observed upload
entry for game 2.04.07, guarded by PE timestamp, image size, and entry bytes.
F10 is intended to install an observer and collect bounded samples. It restores
arguments before forwarding the call and is intended not to change pose or
mesh values. Installing a hook still changes executable routing, so it is
not an external read-only tool. **It is unbuilt and unverified; do not install
it for ordinary play.** It does not implement sliders or physics.

The assembly wrapper is intended to preserve GP/XMM arguments, flags, MXCSR,
and the x87 control word. It does not preserve upper YMM state or arbitrary
x87 stack state. Its ABI test suite has not yet run. Existing-hook chaining
and module identification need further review before use alongside plugins.
Captured addresses/bytes are local diagnostics and must not be committed.

Still required before a working runtime release:

1. Build and pass observer ABI tests; review exception/unload behavior and coexistence with existing hooks.
2. Verify upload argument semantics, actor ownership, buffer lifetime, and the relationship to rendered Kliff geometry.
3. Establish a supported deformation path and bind the solver's outputs to it.
4. Verify naked/clothed visibility and restore original behavior when clothes are worn.
5. Connect validated in-game slider UI to bounded fitting parameters and persistent settings.
6. Validate movement, camera distance/LODs, save loading, and compatibility in the actual game.

Matching exported function names or signatures is not proof of a safe API or
visible deformation. Existing BodyPhysics geometry exports were inspected
offline, but no usable source/SDK was available and their setter semantics
were not established. No guessed exports have been called.
