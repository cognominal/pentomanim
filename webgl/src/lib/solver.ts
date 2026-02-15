import { BOARD_COLS, BOARD_ROWS, PIECES, PIECE_ORDER, normalize } from './pentomino';
import type { Placement, PieceName, Coord } from './pentomino';

type Board = (PieceName | null)[][];

type SolverCtx = {
  rows: number;
  cols: number;
};

function buildBoard(ctx: SolverCtx): Board {
  return Array.from({ length: ctx.rows }, () => Array.from({ length: ctx.cols }, () => null));
}

function canPlace(ctx: SolverCtx, board: Board, cells: Coord[]): boolean {
  for (const [r, c] of cells) {
    if (r < 0 || r >= ctx.rows || c < 0 || c >= ctx.cols) {
      return false;
    }
    if (board[r][c] !== null) {
      return false;
    }
  }
  return true;
}

function write(board: Board, cells: Coord[], value: PieceName | null): void {
  for (const [r, c] of cells) {
    board[r][c] = value;
  }
}

function firstEmpty(ctx: SolverCtx, board: Board): Coord | null {
  // Explore anchors along the shortest board dimension first.
  if (ctx.rows <= ctx.cols) {
    for (let c = 0; c < ctx.cols; c += 1) {
      for (let r = 0; r < ctx.rows; r += 1) {
        if (board[r][c] === null) {
          return [r, c];
        }
      }
    }
  } else {
    for (let r = 0; r < ctx.rows; r += 1) {
      for (let c = 0; c < ctx.cols; c += 1) {
        if (board[r][c] === null) {
          return [r, c];
        }
      }
    }
  }
  return null;
}

function hasOnlyFiveMultipleEmptyRegions(ctx: SolverCtx, board: Board): boolean {
  const visited: boolean[][] = Array.from({ length: ctx.rows }, () =>
    Array.from({ length: ctx.cols }, () => false),
  );
  const deltas: Coord[] = [
    [-1, 0],
    [1, 0],
    [0, -1],
    [0, 1],
  ];

  for (let r = 0; r < ctx.rows; r += 1) {
    for (let c = 0; c < ctx.cols; c += 1) {
      if (board[r][c] !== null || visited[r][c]) {
        continue;
      }

      let regionSize = 0;
      const stack: Coord[] = [[r, c]];
      visited[r][c] = true;

      while (stack.length > 0) {
        const [cr, cc] = stack.pop() as Coord;
        regionSize += 1;

        for (const [dr, dc] of deltas) {
          const nr = cr + dr;
          const nc = cc + dc;
          if (nr < 0 || nr >= ctx.rows || nc < 0 || nc >= ctx.cols) {
            continue;
          }
          if (visited[nr][nc] || board[nr][nc] !== null) {
            continue;
          }
          visited[nr][nc] = true;
          stack.push([nr, nc]);
        }
      }

      if (regionSize % 5 !== 0) {
        return false;
      }
    }
  }

  return true;
}

function uniqueOrientations(cells: Coord[]): Coord[][] {
  const seen = new Set<string>();
  const variants: Coord[][] = [];
  for (const flipped of [false, true]) {
    for (let k = 0; k < 4; k += 1) {
      const variant = normalize(
        cells.map(([r0, c0]) => {
          let x = r0;
          let y = c0;
          if (flipped) {
            y = -y;
          }
          for (let i = 0; i < k; i += 1) {
            const nx = y;
            const ny = -x;
            x = nx;
            y = ny;
          }
          return [x, y] as Coord;
        }),
      );
      const key = variant.map(([r, c]) => `${r},${c}`).join('|');
      if (!seen.has(key)) {
        seen.add(key);
        variants.push(variant);
      }
    }
  }
  return variants;
}

const ORIENTATIONS: Record<PieceName, Coord[][]> = PIECE_ORDER.reduce((acc, name) => {
  acc[name] = uniqueOrientations(PIECES[name]);
  return acc;
}, {} as Record<PieceName, Coord[][]>);

export type TraceEvent = {
  type: 'place' | 'remove';
  placement: Placement;
};

export type PrefixSolutionCount = {
  count: number;
  complete: boolean;
};

function search(ctx: SolverCtx, board: Board, used: Set<PieceName>): Placement[] | null {
  const empty = firstEmpty(ctx, board);
  if (empty === null) {
    return [];
  }

  const [anchorR, anchorC] = empty;
  for (const name of PIECE_ORDER) {
    if (used.has(name)) {
      continue;
    }
    for (const orient of ORIENTATIONS[name]) {
      for (const [cellR, cellC] of orient) {
        const dr = anchorR - cellR;
        const dc = anchorC - cellC;
        const shifted = orient.map(([r, c]) => [r + dr, c + dc] as Coord);
        if (!canPlace(ctx, board, shifted)) {
          continue;
        }

        write(board, shifted, name);
        if (!hasOnlyFiveMultipleEmptyRegions(ctx, board)) {
          write(board, shifted, null);
          continue;
        }
        used.add(name);
        const rest = search(ctx, board, used);
        if (rest !== null) {
          return [{ name, cells: shifted }, ...rest];
        }
        used.delete(name);
        write(board, shifted, null);
      }
    }
  }

  return null;
}

function countSearch(
  ctx: SolverCtx,
  board: Board,
  used: Set<PieceName>,
  currentCount: number,
  maxCount: number,
  limitHit: { value: boolean },
): number {
  if (currentCount >= maxCount) {
    limitHit.value = true;
    return currentCount;
  }

  const empty = firstEmpty(ctx, board);
  if (empty === null) {
    return currentCount + 1;
  }

  const [anchorR, anchorC] = empty;
  let count = currentCount;
  for (const name of PIECE_ORDER) {
    if (used.has(name)) {
      continue;
    }
    for (const orient of ORIENTATIONS[name]) {
      for (const [cellR, cellC] of orient) {
        const dr = anchorR - cellR;
        const dc = anchorC - cellC;
        const shifted = orient.map(([r, c]) => [r + dr, c + dc] as Coord);
        if (!canPlace(ctx, board, shifted)) {
          continue;
        }
        write(board, shifted, name);
        if (!hasOnlyFiveMultipleEmptyRegions(ctx, board)) {
          write(board, shifted, null);
          continue;
        }
        used.add(name);
        count = countSearch(ctx, board, used, count, maxCount, limitHit);
        used.delete(name);
        write(board, shifted, null);
        if (limitHit.value) {
          return count;
        }
      }
    }
  }

  return count;
}

function searchWithTrace(
  ctx: SolverCtx,
  board: Board,
  used: Set<PieceName>,
  trace: TraceEvent[],
  maxTraceEvents: number,
): Placement[] | null {
  const empty = firstEmpty(ctx, board);
  if (empty === null) {
    return [];
  }

  const [anchorR, anchorC] = empty;
  for (const name of PIECE_ORDER) {
    if (used.has(name)) {
      continue;
    }
    for (const orient of ORIENTATIONS[name]) {
      for (const [cellR, cellC] of orient) {
        const dr = anchorR - cellR;
        const dc = anchorC - cellC;
        const shifted = orient.map(([r, c]) => [r + dr, c + dc] as Coord);
        if (!canPlace(ctx, board, shifted)) {
          continue;
        }

        const placement: Placement = { name, cells: shifted };
        write(board, shifted, name);
        if (!hasOnlyFiveMultipleEmptyRegions(ctx, board)) {
          write(board, shifted, null);
          continue;
        }
        used.add(name);
        trace.push({ type: 'place', placement });
        if (trace.length > maxTraceEvents) {
          used.delete(name);
          write(board, shifted, null);
          trace.pop();
          return null;
        }

        const rest = searchWithTrace(ctx, board, used, trace, maxTraceEvents);
        if (rest !== null) {
          return [placement, ...rest];
        }

        used.delete(name);
        write(board, shifted, null);
        trace.push({ type: 'remove', placement });
        if (trace.length > maxTraceEvents) {
          trace.pop();
          return null;
        }
      }
    }
  }

  return null;
}

export function solveFromPlacements(
  fixedPlacements: Placement[],
  rows = BOARD_ROWS,
  cols = BOARD_COLS,
): Placement[] | null {
  const ctx: SolverCtx = { rows, cols };
  const board = buildBoard(ctx);
  const used = new Set<PieceName>();

  for (const p of fixedPlacements) {
    if (used.has(p.name)) {
      return null;
    }
    if (!canPlace(ctx, board, p.cells)) {
      return null;
    }
    write(board, p.cells, p.name);
    used.add(p.name);
  }
  if (!hasOnlyFiveMultipleEmptyRegions(ctx, board)) {
    return null;
  }

  const remainder = search(ctx, board, used);
  if (remainder === null) {
    return null;
  }
  return [...fixedPlacements, ...remainder];
}

export function canApplyPlacement(
  placements: Placement[],
  candidate: Placement,
  rows = BOARD_ROWS,
  cols = BOARD_COLS,
): boolean {
  const ctx: SolverCtx = { rows, cols };
  const board = buildBoard(ctx);
  const seen = new Set<PieceName>();
  for (const p of placements) {
    if (seen.has(p.name)) {
      return false;
    }
    if (!canPlace(ctx, board, p.cells)) {
      return false;
    }
    write(board, p.cells, p.name);
    seen.add(p.name);
  }
  if (seen.has(candidate.name)) {
    return false;
  }
  if (!canPlace(ctx, board, candidate.cells)) {
    return false;
  }
  write(board, candidate.cells, candidate.name);
  return hasOnlyFiveMultipleEmptyRegions(ctx, board);
}

export function solveWithTraceFromPlacements(
  fixedPlacements: Placement[],
  maxTraceEvents = 3000,
  rows = BOARD_ROWS,
  cols = BOARD_COLS,
): { solution: Placement[]; trace: TraceEvent[] } | null {
  const ctx: SolverCtx = { rows, cols };
  const board = buildBoard(ctx);
  const used = new Set<PieceName>();

  for (const p of fixedPlacements) {
    if (used.has(p.name)) {
      return null;
    }
    if (!canPlace(ctx, board, p.cells)) {
      return null;
    }
    write(board, p.cells, p.name);
    used.add(p.name);
  }
  if (!hasOnlyFiveMultipleEmptyRegions(ctx, board)) {
    return null;
  }

  const trace: TraceEvent[] = [];
  const remainder = searchWithTrace(ctx, board, used, trace, maxTraceEvents);
  if (remainder === null) {
    return null;
  }
  return {
    solution: [...fixedPlacements, ...remainder],
    trace,
  };
}

export function countSolutionsFromPlacements(
  fixedPlacements: Placement[],
  maxCount = 200,
  rows = BOARD_ROWS,
  cols = BOARD_COLS,
): PrefixSolutionCount {
  const ctx: SolverCtx = { rows, cols };
  const board = buildBoard(ctx);
  const used = new Set<PieceName>();

  for (const p of fixedPlacements) {
    if (used.has(p.name)) {
      return { count: 0, complete: true };
    }
    if (!canPlace(ctx, board, p.cells)) {
      return { count: 0, complete: true };
    }
    write(board, p.cells, p.name);
    used.add(p.name);
  }
  if (!hasOnlyFiveMultipleEmptyRegions(ctx, board)) {
    return { count: 0, complete: true };
  }

  const limitHit = { value: false };
  const count = countSearch(ctx, board, used, 0, Math.max(1, maxCount), limitHit);
  return {
    count,
    complete: !limitHit.value,
  };
}
