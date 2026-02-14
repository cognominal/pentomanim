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
- `6x10` WebGL board with square cells.
- Piece picker (`F I L P N T U V W X Y Z`).
- Rotate/flip/reset active piece.
- Ghost placement preview.
- Manual placement and removal.
- Solve from current prefix.
- Animated solve with progressive acceleration.
- Step counter (`steps used`).
- Solved history pane (scrollable), click to load into Solver.
- Connected-empty-region pruning (`empty region square count % 5 === 0`).

## Controls
- Select piece: click piece tile or press its letter key.
- Rotate right: `R`
- Rotate left: `Shift+R`
- Flip: `X`
- Clear ghost hover: `Esc`
- Place: click board when ghost is valid.
- Remove: click a placed piece cell.

## Key Source Files
- `/Users/cog/mine/pentomanim/webgl/src/App.svelte`
- `/Users/cog/mine/pentomanim/webgl/src/lib/pentomino.ts`
- `/Users/cog/mine/pentomanim/webgl/src/lib/solver.ts`
- `/Users/cog/mine/pentomanim/webgl/src/lib/BoardWebGL.svelte`
