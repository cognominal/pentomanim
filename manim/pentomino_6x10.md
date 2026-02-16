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

<!-- AUTO-SYNC:START -->
source_file: pentomino_6x10.py
source_sha256: fcc9f8cbdfcf66298c6f86714f8b9be48eb876205f52ca8fd68c36e73c3c9ee4
source_mtime_utc: 2026-02-14T09:35:38+00:00
synced_at_utc: 2026-02-16T14:06:21+00:00
scene: PentominoFillAnimation
render_cmd: manim -qh pentomino_6x10.py PentominoFillAnimation
<!-- AUTO-SYNC:END -->
