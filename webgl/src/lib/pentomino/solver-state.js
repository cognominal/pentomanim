import { solveDlx, solveDlxWithTrace } from './dlx';
import { generateExactCoverModel, } from './placement-gen';
function filterRows(rows, placed) {
    if (placed.size === 0) {
        return rows;
    }
    const selected = rows.filter((r) => placed.has(r.id));
    if (selected.length !== placed.size) {
        return [];
    }
    const usedCols = new Set();
    for (const row of selected) {
        for (const c of row.columns) {
            if (usedCols.has(c)) {
                return [];
            }
            usedCols.add(c);
        }
    }
    return rows.filter((row) => {
        if (placed.has(row.id)) {
            return true;
        }
        for (const c of row.columns) {
            if (usedCols.has(c)) {
                return false;
            }
        }
        return true;
    });
}
export class SolverState {
    constructor(box) {
        Object.defineProperty(this, "model", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "dlxRows", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        this.model = generateExactCoverModel(box);
        this.dlxRows = this.model.rows.map((r) => ({
            id: r.placementId,
            columns: r.columns,
        }));
    }
    placementsCount() {
        return this.model.placements.length;
    }
    placementById(id) {
        return this.model.placements.find((p) => p.id === id) ?? null;
    }
    placementsByIds(ids) {
        return ids
            .map((id) => this.placementById(id))
            .filter((placement) => placement !== null);
    }
    solve(placedIds = [], maxSolutions = 1) {
        const placed = new Set(placedIds);
        const rows = filterRows(this.dlxRows, placed);
        if (rows.length === 0) {
            return [];
        }
        return solveDlx(this.model.columns, rows, maxSolutions)
            .map((s) => s.rowIds);
    }
    hint(placedIds) {
        const solution = this.solve(placedIds, 1)[0];
        if (!solution) {
            return null;
        }
        const placed = new Set(placedIds);
        const next = solution.find((id) => !placed.has(id));
        if (next === undefined) {
            return null;
        }
        return this.placementById(next);
    }
    solveWithTrace(placedIds = [], maxSolutions = 1, maxTraceEvents = 20000) {
        const placed = new Set(placedIds);
        const rows = filterRows(this.dlxRows, placed);
        if (rows.length === 0) {
            return { solutions: [], trace: [], seedPlacements: [] };
        }
        const raw = solveDlxWithTrace(this.model.columns, rows, maxSolutions, maxTraceEvents);
        const toPlacement = (event) => {
            const placement = this.placementById(event.rowId);
            if (!placement) {
                return null;
            }
            return { type: event.type, placement };
        };
        return {
            solutions: raw.solutions.map((s) => s.rowIds),
            trace: raw.trace
                .map(toPlacement)
                .filter((event) => event !== null),
            seedPlacements: this.placementsByIds(placedIds),
        };
    }
}
//# sourceMappingURL=solver-state.js.map