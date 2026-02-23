import { describe, expect, test } from 'bun:test';
import { solveDlx } from '../../src/lib/pentomino/dlx';

describe('dlx', () => {
  test('solves a tiny exact-cover matrix', () => {
    const rows = [
      { id: 0, columns: [0, 2] },
      { id: 1, columns: [1, 3] },
      { id: 2, columns: [0, 3] },
      { id: 3, columns: [1, 2] },
    ];
    const out = solveDlx(4, rows, 2);
    expect(out.length).toBeGreaterThan(0);
  });
});
