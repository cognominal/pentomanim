import type { BoxSize, Placement3D } from './placement-gen';

export type SolveTraceEvent = {
  type: 'place' | 'remove';
  placement: Placement3D;
};

export type SolverRequest =
  | { type: 'init'; box: BoxSize }
  | { type: 'solve'; placedIds?: number[]; maxSolutions?: number }
  | {
      type: 'animate-solve';
      placedIds?: number[];
      maxSolutions?: number;
      maxTraceEvents?: number;
    }
  | { type: 'hint'; placedIds: number[] };

export type SolverResponse =
  | { type: 'ready'; placements: number }
  | { type: 'solved'; solutions: number[][]; firstPlacementSet: Placement3D[] }
  | {
      type: 'solve-trace';
      solutions: number[][];
      firstPlacementSet: Placement3D[];
      seedPlacements: Placement3D[];
      trace: SolveTraceEvent[];
    }
  | { type: 'hint'; placement: Placement3D | null }
  | { type: 'error'; message: string };
