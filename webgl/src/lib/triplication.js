import { PIECE_ORDER, PIECES, normalize } from './pentomino';
function key(r, c) {
    return `${r},${c}`;
}
function uniqueOrientations(cells) {
    const seen = new Set();
    const variants = [];
    for (const flipped of [false, true]) {
        for (let k = 0; k < 4; k += 1) {
            const variant = normalize(cells.map(([r0, c0]) => {
                let x = r0;
                let y = c0;
                if (flipped)
                    y = -y;
                for (let i = 0; i < k; i += 1) {
                    const nx = y;
                    const ny = -x;
                    x = nx;
                    y = ny;
                }
                return [x, y];
            }));
            const signature = variant.map(([r, c]) => key(r, c)).join('|');
            if (!seen.has(signature)) {
                seen.add(signature);
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
function triplicatePieceCells(piece) {
    const base = PIECES[piece];
    const maxR = Math.max(...base.map((c) => c[0])) + 1;
    const maxC = Math.max(...base.map((c) => c[1])) + 1;
    const cells = [];
    for (const [r, c] of base) {
        for (let dr = 0; dr < 3; dr += 1) {
            for (let dc = 0; dc < 3; dc += 1) {
                cells.push([r * 3 + dr, c * 3 + dc]);
            }
        }
    }
    return {
        rows: maxR * 3,
        cols: maxC * 3,
        cells,
    };
}
function buildMaskCtx(rows, cols, maskCells) {
    const allowedKeys = new Set(maskCells.map(([r, c]) => key(r, c)));
    const sortedMask = [...maskCells].sort(([ar, ac], [br, bc]) => (ar === br ? ac - bc : ar - br));
    return { rows, cols, allowedKeys, sortedMask };
}
function hasOnlyFiveMultipleVoidRegions(ctx, filled) {
    const visited = new Set();
    const deltas = [
        [-1, 0],
        [1, 0],
        [0, -1],
        [0, 1],
    ];
    for (const [r, c] of ctx.sortedMask) {
        const start = key(r, c);
        if (filled.has(start) || visited.has(start)) {
            continue;
        }
        let regionSize = 0;
        const stack = [[r, c]];
        visited.add(start);
        while (stack.length > 0) {
            const [cr, cc] = stack.pop();
            regionSize += 1;
            for (const [dr, dc] of deltas) {
                const nr = cr + dr;
                const nc = cc + dc;
                if (nr < 0 || nr >= ctx.rows || nc < 0 || nc >= ctx.cols) {
                    continue;
                }
                const k = key(nr, nc);
                if (!ctx.allowedKeys.has(k) || filled.has(k) || visited.has(k)) {
                    continue;
                }
                visited.add(k);
                stack.push([nr, nc]);
            }
        }
        if (regionSize % 5 !== 0) {
            return false;
        }
    }
    return true;
}
function solveMaskWithPieces(ctx, pieceOrder, maxNodes) {
    const used = new Set();
    const filled = new Set();
    const placements = [];
    let nodes = 0;
    function firstEmpty() {
        for (const [r, c] of ctx.sortedMask) {
            if (!filled.has(key(r, c))) {
                return [r, c];
            }
        }
        return null;
    }
    function canPlace(cells) {
        for (const [r, c] of cells) {
            const k = key(r, c);
            if (!ctx.allowedKeys.has(k) || filled.has(k)) {
                return false;
            }
        }
        return true;
    }
    function place(p) {
        placements.push(p);
        used.add(p.name);
        for (const [r, c] of p.cells) {
            filled.add(key(r, c));
        }
    }
    function unplace() {
        const p = placements.pop();
        used.delete(p.name);
        for (const [r, c] of p.cells) {
            filled.delete(key(r, c));
        }
    }
    function dfs() {
        nodes += 1;
        if (nodes > maxNodes) {
            return false;
        }
        const anchor = firstEmpty();
        if (!anchor) {
            return true;
        }
        const [ar, ac] = anchor;
        for (const name of pieceOrder) {
            if (used.has(name)) {
                continue;
            }
            for (const orient of ORIENTATIONS[name]) {
                for (const [cr, cc] of orient) {
                    const dr = ar - cr;
                    const dc = ac - cc;
                    const shifted = orient.map(([r, c]) => [r + dr, c + dc]);
                    if (!canPlace(shifted)) {
                        continue;
                    }
                    place({ name, cells: shifted });
                    if (hasOnlyFiveMultipleVoidRegions(ctx, filled) && dfs()) {
                        return true;
                    }
                    unplace();
                }
            }
        }
        return false;
    }
    const solved = dfs();
    if (solved) {
        return { solution: placements.map((p) => ({ name: p.name, cells: [...p.cells] })), aborted: false };
    }
    return { solution: null, aborted: nodes > maxNodes };
}
function solveMaskWithTrace(ctx, pieceOrder, maxNodes) {
    const used = new Set();
    const filled = new Set();
    const placements = [];
    const trace = [];
    let nodes = 0;
    function firstEmpty() {
        for (const [r, c] of ctx.sortedMask) {
            if (!filled.has(key(r, c))) {
                return [r, c];
            }
        }
        return null;
    }
    function canPlace(cells) {
        for (const [r, c] of cells) {
            const k = key(r, c);
            if (!ctx.allowedKeys.has(k) || filled.has(k)) {
                return false;
            }
        }
        return true;
    }
    function place(p) {
        placements.push(p);
        used.add(p.name);
        for (const [r, c] of p.cells) {
            filled.add(key(r, c));
        }
        trace.push({ type: 'place', placement: p });
    }
    function unplace() {
        const p = placements.pop();
        used.delete(p.name);
        for (const [r, c] of p.cells) {
            filled.delete(key(r, c));
        }
        trace.push({ type: 'remove', placement: p });
    }
    function dfs() {
        nodes += 1;
        if (nodes > maxNodes) {
            return false;
        }
        const anchor = firstEmpty();
        if (!anchor) {
            return true;
        }
        const [ar, ac] = anchor;
        for (const name of pieceOrder) {
            if (used.has(name)) {
                continue;
            }
            for (const orient of ORIENTATIONS[name]) {
                for (const [cr, cc] of orient) {
                    const dr = ar - cr;
                    const dc = ac - cc;
                    const shifted = orient.map(([r, c]) => [r + dr, c + dc]);
                    if (!canPlace(shifted)) {
                        continue;
                    }
                    const p = { name, cells: shifted };
                    place(p);
                    if (hasOnlyFiveMultipleVoidRegions(ctx, filled) && dfs()) {
                        return true;
                    }
                    unplace();
                }
            }
        }
        return false;
    }
    const solved = dfs();
    if (solved) {
        return {
            solution: placements.map((p) => ({ name: p.name, cells: [...p.cells] })),
            trace,
            aborted: false,
        };
    }
    return { solution: null, trace, aborted: nodes > maxNodes };
}
function shuffled(values, rand) {
    const out = [...values];
    for (let i = out.length - 1; i > 0; i -= 1) {
        const j = Math.floor(rand() * (i + 1));
        [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
}
function validateTriplicationPrefix(problem, fixedPlacements) {
    const ctx = buildMaskCtx(problem.rows, problem.cols, problem.maskCells);
    const baseFilled = new Set();
    const used = new Set();
    for (const p of fixedPlacements) {
        if (!problem.selectedPieces.includes(p.name) || used.has(p.name)) {
            return null;
        }
        for (const [r, c] of p.cells) {
            const k = key(r, c);
            if (!ctx.allowedKeys.has(k) || baseFilled.has(k)) {
                return null;
            }
            baseFilled.add(k);
        }
        used.add(p.name);
    }
    if (!hasOnlyFiveMultipleVoidRegions(ctx, baseFilled)) {
        return null;
    }
    return { ctx, baseFilled, used };
}
export function createTriplicationProblem(maxAttempts = 300, maxNodes = 300000) {
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        const piecePool = shuffled(PIECE_ORDER, Math.random);
        const triplicatedPiece = piecePool[0];
        const { rows, cols, cells } = triplicatePieceCells(triplicatedPiece);
        const selectedPieces = shuffled(PIECE_ORDER, Math.random).slice(0, 9);
        const ctx = buildMaskCtx(rows, cols, cells);
        const solve = solveMaskWithPieces(ctx, selectedPieces, maxNodes);
        if (solve.solution !== null) {
            return {
                triplicatedPiece,
                rows,
                cols,
                maskCells: cells,
                selectedPieces,
            };
        }
    }
    return null;
}
export function canApplyTriplicationPlacement(problem, placements, candidate) {
    const ctx = buildMaskCtx(problem.rows, problem.cols, problem.maskCells);
    const filled = new Set();
    const used = new Set();
    for (const p of placements) {
        if (!problem.selectedPieces.includes(p.name) || used.has(p.name)) {
            return false;
        }
        for (const [r, c] of p.cells) {
            const k = key(r, c);
            if (!ctx.allowedKeys.has(k) || filled.has(k)) {
                return false;
            }
            filled.add(k);
        }
        used.add(p.name);
    }
    if (!problem.selectedPieces.includes(candidate.name) || used.has(candidate.name)) {
        return false;
    }
    for (const [r, c] of candidate.cells) {
        const k = key(r, c);
        if (!ctx.allowedKeys.has(k) || filled.has(k)) {
            return false;
        }
        filled.add(k);
    }
    return hasOnlyFiveMultipleVoidRegions(ctx, filled);
}
export function solveTriplicationFromPlacements(problem, fixedPlacements, maxNodes = 300000) {
    const prefix = validateTriplicationPrefix(problem, fixedPlacements);
    if (!prefix) {
        return null;
    }
    const { ctx, baseFilled, used } = prefix;
    const remainderPieces = problem.selectedPieces.filter((name) => !used.has(name));
    const reducedCtx = {
        ...ctx,
        sortedMask: ctx.sortedMask.filter(([r, c]) => !baseFilled.has(key(r, c))),
    };
    const solve = solveMaskWithPieces(reducedCtx, remainderPieces, maxNodes);
    if (!solve.solution) {
        return null;
    }
    return [...fixedPlacements, ...solve.solution];
}
export function solveTriplicationWithTraceFromPlacements(problem, fixedPlacements, maxNodes = 300000) {
    const prefix = validateTriplicationPrefix(problem, fixedPlacements);
    if (!prefix) {
        return null;
    }
    const { ctx, baseFilled, used } = prefix;
    const remainderPieces = problem.selectedPieces.filter((name) => !used.has(name));
    const reducedCtx = {
        ...ctx,
        sortedMask: ctx.sortedMask.filter(([r, c]) => !baseFilled.has(key(r, c))),
    };
    const traced = solveMaskWithTrace(reducedCtx, remainderPieces, maxNodes);
    if (!traced.solution) {
        return null;
    }
    return { solution: [...fixedPlacements, ...traced.solution], trace: traced.trace };
}
//# sourceMappingURL=triplication.js.map