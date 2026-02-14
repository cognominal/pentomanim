export const BOARD_ROWS = 6;
export const BOARD_COLS = 10;
export const PIECE_ORDER = ['F', 'I', 'L', 'P', 'N', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];
export const PIECES = {
    F: [[0, 1], [1, 0], [1, 1], [1, 2], [2, 0]],
    I: [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]],
    L: [[0, 0], [1, 0], [2, 0], [3, 0], [3, 1]],
    P: [[0, 0], [0, 1], [1, 0], [1, 1], [2, 0]],
    N: [[0, 0], [1, 0], [1, 1], [2, 1], [3, 1]],
    T: [[0, 0], [0, 1], [0, 2], [1, 1], [2, 1]],
    U: [[0, 0], [0, 2], [1, 0], [1, 1], [1, 2]],
    V: [[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]],
    W: [[0, 0], [1, 0], [1, 1], [2, 1], [2, 2]],
    X: [[0, 1], [1, 0], [1, 1], [1, 2], [2, 1]],
    Y: [[0, 1], [1, 1], [2, 0], [2, 1], [3, 1]],
    Z: [[0, 0], [0, 1], [1, 1], [2, 1], [2, 2]],
};
export const PIECE_COLORS = {
    F: '#c98592',
    I: '#c6a07a',
    L: '#ccb57f',
    P: '#78b39f',
    N: '#6ea8b0',
    T: '#638faa',
    U: '#7f88b7',
    V: '#8574af',
    W: '#9b7eb9',
    X: '#c07690',
    Y: '#c89a70',
    Z: '#7ab1a8',
};
export function normalize(cells) {
    const minR = Math.min(...cells.map((c) => c[0]));
    const minC = Math.min(...cells.map((c) => c[1]));
    return cells
        .map(([r, c]) => [r - minR, c - minC])
        .sort(([ar, ac], [br, bc]) => (ar === br ? ac - bc : ar - br));
}
export function transform(cells, rotation, flipped) {
    const out = [];
    for (const [r0, c0] of cells) {
        let x = r0;
        let y = c0;
        if (flipped) {
            y = -y;
        }
        for (let i = 0; i < rotation % 4; i += 1) {
            const nx = y;
            const ny = -x;
            x = nx;
            y = ny;
        }
        out.push([x, y]);
    }
    return normalize(out);
}
export function cellsForPose(name, pose) {
    return transform(PIECES[name], pose.rotation, pose.flipped);
}
export function placeAtAnchor(cells, anchorRow, anchorCol) {
    return cells.map(([r, c]) => [r + anchorRow, c + anchorCol]);
}
export function inBounds(cells) {
    return cells.every(([r, c]) => r >= 0 && r < BOARD_ROWS && c >= 0 && c < BOARD_COLS);
}
export function placementKey(placement) {
    const body = [...placement.cells]
        .sort(([ar, ac], [br, bc]) => (ar === br ? ac - bc : ar - br))
        .map(([r, c]) => `${r}:${c}`)
        .join('|');
    return `${placement.name}:${body}`;
}
export function solutionKey(placements) {
    return [...placements]
        .sort((a, b) => (a.name < b.name ? -1 : 1))
        .map(placementKey)
        .join('||');
}
//# sourceMappingURL=pentomino.js.map