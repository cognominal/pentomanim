# 3D Pentomino Architecture

## Layout

- `src/lib/pentomino/pieces.ts`: base piece definitions.
- `src/lib/pentomino/orientations.ts`: unique 3D rotations.
- `src/lib/pentomino/placement-gen.ts`: legal placements and exact-cover rows.
- `src/lib/pentomino/dlx.ts`: dancing-links exact-cover solver.
- `src/lib/pentomino/solver-state.ts`: stateful solve/hint facade.
- `src/lib/pentomino/solver.worker.ts`: worker API.
- `src/lib/three/scene.ts`: three.js board rendering.
- `src/lib/three/interaction.ts`: raycast pick helper.
- `src/lib/pages/Pentomino3DPage.svelte`: UI prototype.

## Constraints

For a 3x4x5 box:

- 60 voxel occupancy constraints.
- 12 piece-usage constraints.
- 72 exact-cover columns total.
