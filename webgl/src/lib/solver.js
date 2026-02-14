import { BOARD_COLS, BOARD_ROWS, PIECES, PIECE_ORDER, normalize } from './pentomino';
function buildBoard() {
    return Array.from({ length: BOARD_ROWS }, () => Array.from({ length: BOARD_COLS }, () => null));
}
function canPlace(board, cells) {
    for (const [r, c] of cells) {
        if (r < 0 || r >= BOARD_ROWS || c < 0 || c >= BOARD_COLS) {
            return false;
        }
        if (board[r][c] !== null) {
            return false;
        }
    }
    return true;
}
function write(board, cells, value) {
    for (const [r, c] of cells) {
        board[r][c] = value;
    }
}
function firstEmpty(board) {
    // Explore anchors along the shortest board dimension first.
    // For 6x10 this means scanning column-major to reduce fragmented voids earlier.
    if (BOARD_ROWS <= BOARD_COLS) {
        for (let c = 0; c < BOARD_COLS; c += 1) {
            for (let r = 0; r < BOARD_ROWS; r += 1) {
                if (board[r][c] === null) {
                    return [r, c];
                }
            }
        }
    }
    else {
        for (let r = 0; r < BOARD_ROWS; r += 1) {
            for (let c = 0; c < BOARD_COLS; c += 1) {
                if (board[r][c] === null) {
                    return [r, c];
                }
            }
        }
    }
    return null;
}
function hasOnlyFiveMultipleEmptyRegions(board) {
    const visited = Array.from({ length: BOARD_ROWS }, () => Array.from({ length: BOARD_COLS }, () => false));
    const deltas = [
        [-1, 0],
        [1, 0],
        [0, -1],
        [0, 1],
    ];
    for (let r = 0; r < BOARD_ROWS; r += 1) {
        for (let c = 0; c < BOARD_COLS; c += 1) {
            if (board[r][c] !== null || visited[r][c]) {
                continue;
            }
            let regionSize = 0;
            const stack = [[r, c]];
            visited[r][c] = true;
            while (stack.length > 0) {
                const [cr, cc] = stack.pop();
                regionSize += 1;
                for (const [dr, dc] of deltas) {
                    const nr = cr + dr;
                    const nc = cc + dc;
                    if (nr < 0 || nr >= BOARD_ROWS || nc < 0 || nc >= BOARD_COLS) {
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
function uniqueOrientations(cells) {
    const seen = new Set();
    const variants = [];
    for (const flipped of [false, true]) {
        for (let k = 0; k < 4; k += 1) {
            const variant = normalize(cells.map(([r0, c0]) => {
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
                return [x, y];
            }));
            const key = variant.map(([r, c]) => `${r},${c}`).join('|');
            if (!seen.has(key)) {
                seen.add(key);
                variants.push(variant);
            }
        }
    }
    return variants;
}
const ORIENTATIONS = PIECE_ORDER.reduce((acc, name) => {
    acc[name] = uniqueOrientations(PIECES[name]);
    return acc;
}, {});
function search(board, used) {
    const empty = firstEmpty(board);
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
                const shifted = orient.map(([r, c]) => [r + dr, c + dc]);
                if (!canPlace(board, shifted)) {
                    continue;
                }
                write(board, shifted, name);
                if (!hasOnlyFiveMultipleEmptyRegions(board)) {
                    write(board, shifted, null);
                    continue;
                }
                used.add(name);
                const rest = search(board, used);
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
function searchWithTrace(board, used, trace, maxTraceEvents) {
    const empty = firstEmpty(board);
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
                const shifted = orient.map(([r, c]) => [r + dr, c + dc]);
                if (!canPlace(board, shifted)) {
                    continue;
                }
                const placement = { name, cells: shifted };
                write(board, shifted, name);
                if (!hasOnlyFiveMultipleEmptyRegions(board)) {
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
                const rest = searchWithTrace(board, used, trace, maxTraceEvents);
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
export function solveFromPlacements(fixedPlacements) {
    const board = buildBoard();
    const used = new Set();
    for (const p of fixedPlacements) {
        if (used.has(p.name)) {
            return null;
        }
        if (!canPlace(board, p.cells)) {
            return null;
        }
        write(board, p.cells, p.name);
        used.add(p.name);
    }
    if (!hasOnlyFiveMultipleEmptyRegions(board)) {
        return null;
    }
    const remainder = search(board, used);
    if (remainder === null) {
        return null;
    }
    return [...fixedPlacements, ...remainder];
}
export function canApplyPlacement(placements, candidate) {
    const board = buildBoard();
    const seen = new Set();
    for (const p of placements) {
        if (seen.has(p.name)) {
            return false;
        }
        if (!canPlace(board, p.cells)) {
            return false;
        }
        write(board, p.cells, p.name);
        seen.add(p.name);
    }
    if (seen.has(candidate.name)) {
        return false;
    }
    if (!canPlace(board, candidate.cells)) {
        return false;
    }
    write(board, candidate.cells, candidate.name);
    return hasOnlyFiveMultipleEmptyRegions(board);
}
export function solveWithTraceFromPlacements(fixedPlacements, maxTraceEvents = 3000) {
    const board = buildBoard();
    const used = new Set();
    for (const p of fixedPlacements) {
        if (used.has(p.name)) {
            return null;
        }
        if (!canPlace(board, p.cells)) {
            return null;
        }
        write(board, p.cells, p.name);
        used.add(p.name);
    }
    if (!hasOnlyFiveMultipleEmptyRegions(board)) {
        return null;
    }
    const trace = [];
    const remainder = searchWithTrace(board, used, trace, maxTraceEvents);
    if (remainder === null) {
        return null;
    }
    return {
        solution: [...fixedPlacements, ...remainder],
        trace,
    };
}
//# sourceMappingURL=solver.js.map