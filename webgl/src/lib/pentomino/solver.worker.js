/// <reference lib="webworker" />
import { SolverState } from './solver-state';
let state = null;
self.onmessage = (event) => {
    const req = event.data;
    try {
        if (req.type === 'init') {
            state = new SolverState(req.box);
            const res = {
                type: 'ready',
                placements: state.placementsCount(),
            };
            self.postMessage(res);
            return;
        }
        if (!state) {
            self.postMessage({ type: 'error', message: 'Solver not initialized' });
            return;
        }
        if (req.type === 'solve') {
            const solutions = state.solve(req.placedIds ?? [], req.maxSolutions ?? 1);
            const firstPlacementSet = solutions.length
                ? state.placementsByIds(solutions[0])
                : [];
            const res = {
                type: 'solved',
                solutions,
                firstPlacementSet,
            };
            self.postMessage(res);
            return;
        }
        if (req.type === 'animate-solve') {
            const solved = state.solveWithTrace(req.placedIds ?? [], req.maxSolutions ?? 1, req.maxTraceEvents ?? 20000);
            const firstPlacementSet = solved.solutions.length
                ? state.placementsByIds(solved.solutions[0])
                : [];
            const res = {
                type: 'solve-trace',
                solutions: solved.solutions,
                firstPlacementSet,
                seedPlacements: solved.seedPlacements,
                trace: solved.trace,
            };
            self.postMessage(res);
            return;
        }
        if (req.type === 'hint') {
            const placement = state.hint(req.placedIds);
            const res = { type: 'hint', placement };
            self.postMessage(res);
        }
    }
    catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        self.postMessage({ type: 'error', message });
    }
};
export {};
//# sourceMappingURL=solver.worker.js.map