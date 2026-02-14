# Pentomanim

This repository contains two pentomino apps:

1. `manim/`: Python + Manim animation scripts.
2. `webgl/`: interactive Svelte + TypeScript + WebGL pentomino solver UI.

## 1) Manim App

Location: `/Users/cog/mine/pentomanim/manim`

### Files
- `pentomino_6x10.py`
- `pentomino_6x10_five.py`

### What it does
- Defines pentomino shapes and a DFS tiling solver.
- Renders animation scenes showing pentomino placements on a `6x10` rectangle.
- `pentomino_6x10_five.py` builds five unique solved rectangles and lays them out.

### Run
From repo root:

```bash
manim -pqh manim/pentomino_6x10_five.py PentominoFiveRectangles
```

Optional quality presets:

```bash
manim -pql manim/pentomino_6x10_five.py PentominoFiveRectangles  # low
manim -pqh manim/pentomino_6x10_five.py PentominoFiveRectangles  # high
```

Output videos are written under:
- `/Users/cog/mine/pentomanim/manim/media/videos/...`

## 2) WebGL App

Location: `/Users/cog/mine/pentomanim/webgl`

### What it does
- Interactive pentomino placement board (`6x10`) rendered with WebGL.
- Piece picker with rotate/flip controls.
- Manual solve + automatic solve from current prefix.
- Animated solve with progressive speed control.
- Solved-history pane: click a solved rectangle to load it into Solver.
- Pruning rule for search efficiency: connected empty regions must have a square count divisible by 5.

### Install

```bash
cd /Users/cog/mine/pentomanim/webgl
bun install
```

### Run dev server

```bash
bun run dev
```

### Build

```bash
bun run build
```

### Preview build

```bash
bun run preview
```

## Notes
- The WebGL app is the interactive rewrite of the Manim logic, with additional UI features.
- Solver behavior and orientation logic are implemented in:
  - `/Users/cog/mine/pentomanim/webgl/src/lib/pentomino.ts`
  - `/Users/cog/mine/pentomanim/webgl/src/lib/solver.ts`
