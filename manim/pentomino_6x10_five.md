# Spec: `pentomino_6x10_five.py`

## Purpose

Find and animate five unique `6x10` pentomino tilings, showing each solved
board as a scaled thumbnail.

## Main Scene

- `PentominoFiveRectangles`

## Core Behavior

- Uses `DFSSolver` with randomized ordering (seeded) to produce candidate full
  tilings.
- Collects unique solutions via canonical signature until `solve_count` is met.
- Animates each solution lifecycle.

Per-solution animation flow:

- Place pieces from top gallery onto the main board.
- Snapshot the solved board.
- Scale/move snapshot into right-side solved slots.
- Clear board and restore top gallery for next solution.

## Uniqueness / Search

- Search is full DFS with random shuffle of:
  - Remaining piece names.
  - Orientations.
  - Anchor cells per orientation.
- Uniqueness is determined by normalized solution signature.

## Inputs / Config

- Tunables in `construct()`:
  - `solve_count` (default `5`)
  - `max_attempts` in `find_unique_solutions`
  - `step_time`, `board_cell`, `top_cell`, `solved_scale`

## Output

- Standard Manim video output under media folders.

<!-- AUTO-SYNC:START -->
source_file: pentomino_6x10_five.py
source_sha256: 2a8c01593a4b3b1c5099cc86bb25554e7d286dd99c87378e1060ab16576643af
source_mtime_utc: 2026-02-14T10:13:01+00:00
synced_at_utc: 2026-02-16T14:08:20+00:00
scene: PentominoFiveRectangles
render_cmd: manim -qh pentomino_6x10_five.py PentominoFiveRectangles
<!-- AUTO-SYNC:END -->
