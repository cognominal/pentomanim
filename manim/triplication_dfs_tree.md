# Spec: `triplication_dfs_tree.py`

## Purpose

Animate DFS tree construction for a pentomino triplication solve, with mod-5
pruning emphasis and live `vanilla` vs `mod-5` counters.

## Main Scene

- `TriplicationDFSTreeSeparate` (single displayed tree)

## Core Solver Model

- Triplication board is generated from a triplicated pentomino mask.
- DFS places selected pieces using orientation enumeration.
- Optional mod-5 empty-region pruning is applied during search.
- Trace captures node enter/exit events and cumulative timing/step stats.

## Display Semantics

- Single displayed tree is the mod-5 run.
- Child display policy:
  - Normally show `first`, `second`, and `rightmost` child candidates.
  - On rightmost-chain nodes, show only the rightmost child.
- Depth policy:
  - Default display depth: `3`.
  - Rightmost-chain display depth: `9`.
- Rightmost branch is aligned with first-solution continuation.

## Node Visuals

- Board-only nodes (no per-node text).
- Piece fills use Svelte piece colors.
- Pieces are drawn as continuous fills with outer boundaries.
- No board grid.
- Pruned nodes have dark desaturated red backgrounds.
- Counterfactual descendants (from unpruned trace) are grafted for pruned
  branches.

## HUD Counters

- Three-line table at top:
  - Header: `time-spent`, `step-nr`, `time/step`.
  - Row 1: `vanilla`.
  - Row 2: `mod-5`.
- Counters update during node reveal and end at full totals.

## Timing / Slicing

- Global speed multiplier: `TIME_SCALE`.
- Supports clip rendering via CLI arg:
  - `--slice=START:END`

## Output

- Standard Manim video output under media folders.

<!-- AUTO-SYNC:START -->
source_file: triplication_dfs_tree.py
source_sha256: 3cfe6e3894aaf9c7d424dd24a9c9c8331f22c80711c8ef8cc37fb0a8014f5750
source_mtime_utc: 2026-02-16T01:39:01+00:00
synced_at_utc: 2026-02-16T14:18:36+00:00
scene: TriplicationDFSTreeSeparate
render_cmd: manim -qh triplication_dfs_tree.py TriplicationDFSTreeSeparate
<!-- AUTO-SYNC:END -->
