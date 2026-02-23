import { PIECES_3D } from './pieces';
import type { Vec3 } from './pieces';
import { uniqueOrientations } from './orientations';

export type BoxSize = { x: number; y: number; z: number };

export type Placement3D = {
  id: number;
  piece: string;
  cells: Vec3[];
};

export type ExactCoverRow = {
  placementId: number;
  columns: number[];
};

export type ExactCoverModel = {
  columns: number;
  placements: Placement3D[];
  rows: ExactCoverRow[];
};

export function cellIndex(x: number, y: number, z: number, box: BoxSize): number {
  return z * box.x * box.y + y * box.x + x;
}

export function generateExactCoverModel(box: BoxSize): ExactCoverModel {
  const placements: Placement3D[] = [];
  const rows: ExactCoverRow[] = [];
  const pieceColumnStart = box.x * box.y * box.z;
  let nextId = 0;

  PIECES_3D.forEach((piece, pieceIdx) => {
    const orientations = uniqueOrientations(piece.cells);
    for (const orient of orientations) {
      let maxX = 0;
      let maxY = 0;
      let maxZ = 0;
      for (const [x, y, z] of orient) {
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
        maxZ = Math.max(maxZ, z);
      }
      for (let ox = 0; ox <= box.x - maxX - 1; ox += 1) {
        for (let oy = 0; oy <= box.y - maxY - 1; oy += 1) {
          for (let oz = 0; oz <= box.z - maxZ - 1; oz += 1) {
            const cells = orient.map(([x, y, z]) =>
              [x + ox, y + oy, z + oz] as Vec3);
            const cols = cells.map(([x, y, z]) => cellIndex(x, y, z, box));
            cols.push(pieceColumnStart + pieceIdx);
            placements.push({ id: nextId, piece: piece.name, cells });
            rows.push({ placementId: nextId, columns: cols });
            nextId += 1;
          }
        }
      }
    }
  });

  return {
    columns: pieceColumnStart + PIECES_3D.length,
    placements,
    rows,
  };
}
