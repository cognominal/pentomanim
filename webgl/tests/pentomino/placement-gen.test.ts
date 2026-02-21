import { describe, expect, test } from 'bun:test';
import { generateExactCoverModel } from '../../src/lib/pentomino/placement-gen';

describe('placement generation', () => {
  test('creates the expected number of columns for 3x4x5', () => {
    const model = generateExactCoverModel({ x: 5, y: 4, z: 3 });
    expect(model.columns).toBe(72);
    expect(model.placements.length).toBeGreaterThan(0);
  });
});
