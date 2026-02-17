import { countSolutionsFromPlacements } from './solver';
import type { Placement } from './pentomino';

type CountRequest = {
  requestId: number;
  placements: Placement[];
  rows: number;
  cols: number;
  limit: number;
};

type CountResponse = {
  requestId: number;
  count: number;
  complete: boolean;
};

self.onmessage = (event: MessageEvent<CountRequest>): void => {
  const { requestId, placements, rows, cols, limit } = event.data;
  const result = countSolutionsFromPlacements(placements, limit, rows, cols);
  const response: CountResponse = {
    requestId,
    count: result.count,
    complete: result.complete,
  };
  self.postMessage(response);
};

