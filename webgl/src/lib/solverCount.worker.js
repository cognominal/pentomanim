import { countSolutionsFromPlacements } from './solver';
self.onmessage = (event) => {
    const { requestId, placements, rows, cols, limit } = event.data;
    const result = countSolutionsFromPlacements(placements, limit, rows, cols);
    const response = {
        requestId,
        count: result.count,
        complete: result.complete,
    };
    self.postMessage(response);
};
//# sourceMappingURL=solverCount.worker.js.map