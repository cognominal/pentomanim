export function normalize(cells) {
    let minX = Infinity;
    let minY = Infinity;
    let minZ = Infinity;
    for (const [x, y, z] of cells) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        minZ = Math.min(minZ, z);
    }
    return cells
        .map(([x, y, z]) => [x - minX, y - minY, z - minZ])
        .sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
}
function key(cells) {
    return normalize(cells)
        .map(([x, y, z]) => `${x},${y},${z}`)
        .join('|');
}
function mul(m, v) {
    return [
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    ];
}
function allRotations() {
    const basis = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
    const perms = [
        [0, 1, 2], [0, 2, 1], [1, 0, 2],
        [1, 2, 0], [2, 0, 1], [2, 1, 0],
    ];
    const signs = [-1, 1];
    const out = [];
    for (const [a, b, c] of perms) {
        for (const sx of signs) {
            for (const sy of signs) {
                for (const sz of signs) {
                    const m = [
                        [sx * basis[a][0], sx * basis[a][1], sx * basis[a][2]],
                        [sy * basis[b][0], sy * basis[b][1], sy * basis[b][2]],
                        [sz * basis[c][0], sz * basis[c][1], sz * basis[c][2]],
                    ];
                    const det = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
                        m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
                        m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
                    if (det === 1) {
                        out.push(m);
                    }
                }
            }
        }
    }
    return out;
}
const ROTATIONS = allRotations();
export function uniqueOrientations(cells) {
    const seen = new Set();
    const out = [];
    for (const m of ROTATIONS) {
        const rotated = normalize(cells.map((v) => mul(m, v)));
        const k = key(rotated);
        if (!seen.has(k)) {
            seen.add(k);
            out.push(rotated);
        }
    }
    return out;
}
//# sourceMappingURL=orientations.js.map