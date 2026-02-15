# Pentomino WebGL App

Interactive pentomino solver built with Svelte + TypeScript + WebGL.

## Setup

```bash
cd /Users/cog/mine/pentomanim/webgl
bun install
```

## Run

```bash
bun run dev
```

## Build

```bash
bun run build
```

## Preview Build

```bash
bun run preview
```

## Features
- Two panes (tabs):
  - `Rectangle Solver`
  - `Triplication Solver`
- Rectangle board sizes: `20x3`, `15x4`, `12x5`, `10x6`.
- Square-cell WebGL boards with piece boundaries.
- Piece picker (`F I L P N T U V W X Y Z`) with touch and desktop variants.
- Rotate/flip/reset active piece and transformed active preview.
- Ghost placement preview on board.
- Manual placement/removal by tapping/clicking cells.
- `Solve` from current prefix.
- `Animate Solve` with progressive acceleration and stop/resume behavior.
- Dynamic step counter and speed slider (linear UI, exponential speed mapping).
- Scrollable solved pane for rectangle solver (load solved cards back to solver).
- Triplication mode:
  - generates solvable masked boards from a triplicated pentomino shape,
  - chooses 9 pieces for the puzzle,
  - supports manual solve, auto solve, animate solve,
  - has its own solved pane, with load-back behavior.
- Prefix pruning by empty-region divisibility rule (`region size % 5 === 0`).

## Controls
- Desktop:
  - Select piece: click piece tile or press piece letter.
  - Rotate right: `R`
  - Rotate left: `Shift+R`
  - Flip: `X`
  - Clear ghost: `Esc`
  - Place/remove: click board cells.
- Touch:
  - Select piece from picker.
  - Place/remove: tap board cells.

## Key Source Files
- `/Users/cog/mine/pentomanim/webgl/src/App.svelte`
- `/Users/cog/mine/pentomanim/webgl/src/lib/pentomino.ts`
- `/Users/cog/mine/pentomanim/webgl/src/lib/solver.ts`
- `/Users/cog/mine/pentomanim/webgl/src/lib/triplication.ts`
- `/Users/cog/mine/pentomanim/webgl/src/lib/BoardWebGL.svelte`

## Deploy to Vercel
- Framework preset: `Vite`
- Root directory: `webgl`
- Build command: `bun run build`
- Output directory: `dist`
