# Spec: `pentomino_6x10.py`

## Purpose

Animate DFS placement/backtracking of pentominoes on a `6x10` board.

## Main Scene

- `PentominoFillAnimation`

## Core Behavior

- Uses deterministic piece order (`sorted(PENTOMINOES)`) and orientation
  generation.
- Runs DFS from the first empty-cell anchor.
- Records search events up to `max_steps` (default `100`).

Recorded event kinds:

- `place`
- `remove`

Rendered elements:

- A single board at the bottom.
- A top piece gallery.
- Placed pieces fading in on the board.
- Corresponding top piece fading out/in on place/remove.

## Geometry / Rendering

- Board: `6x10` rectangle outline.
- Piece rendering: filled unit squares plus outer polyomino outline.
- Timeline is event-driven from recorded DFS events.

## Inputs / Config

- No CLI/custom args.
- Key tunables in scene:
  - `SearchState(max_steps=...)`
  - `board_cell`
  - `top_cell`

## Output

- Standard Manim video output under media folders.
