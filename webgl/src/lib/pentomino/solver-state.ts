import { solveDlx, solveDlxWithTrace } from './dlx';
import type { DlxRow } from './dlx';
import type { DlxTraceEvent } from './dlx';
import {
  generateExactCoverModel,
  type BoxSize,
  type ExactCoverModel,
  type Placement3D,
} from './placement-gen';

function filterRows(rows: DlxRow[], placed: Set<number>): DlxRow[] {
  if (placed.size === 0) {
    return rows;
  }
  const selected = rows.filter((r) => placed.has(r.id));
  if (selected.length !== placed.size) {
    return [];
  }

  const usedCols = new Set<number>();
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
  private model: ExactCoverModel;
  private dlxRows: DlxRow[];

  constructor(box: BoxSize) {
    this.model = generateExactCoverModel(box);
    this.dlxRows = this.model.rows.map((r) => ({
      id: r.placementId,
      columns: r.columns,
    }));
  }

  placementsCount(): number {
    return this.model.placements.length;
  }

  placementById(id: number): Placement3D | null {
    return this.model.placements.find((p) => p.id === id) ?? null;
  }

  placementsByIds(ids: number[]): Placement3D[] {
    return ids
      .map((id) => this.placementById(id))
      .filter((placement): placement is Placement3D => placement !== null);
  }

  solve(placedIds: number[] = [], maxSolutions = 1): number[][] {
    const placed = new Set(placedIds);
    const rows = filterRows(this.dlxRows, placed);
    if (rows.length === 0) {
      return [];
    }
    return solveDlx(this.model.columns, rows, maxSolutions)
      .map((s) => s.rowIds);
  }

  hint(placedIds: number[]): Placement3D | null {
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

  solveWithTrace(
    placedIds: number[] = [],
    maxSolutions = 1,
    maxTraceEvents = 20_000,
  ): {
    solutions: number[][];
    trace: Array<{ type: 'place' | 'remove'; placement: Placement3D }>;
    seedPlacements: Placement3D[];
  } {
    const placed = new Set(placedIds);
    const rows = filterRows(this.dlxRows, placed);
    if (rows.length === 0) {
      return { solutions: [], trace: [], seedPlacements: [] };
    }
    const raw = solveDlxWithTrace(
      this.model.columns,
      rows,
      maxSolutions,
      maxTraceEvents,
    );
    const toPlacement = (
      event: DlxTraceEvent,
    ): { type: 'place' | 'remove'; placement: Placement3D } | null => {
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
        .filter(
          (
            event,
          ): event is { type: 'place' | 'remove'; placement: Placement3D } =>
            event !== null,
        ),
      seedPlacements: this.placementsByIds(placedIds),
    };
  }
}
