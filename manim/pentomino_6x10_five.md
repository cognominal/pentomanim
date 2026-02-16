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
