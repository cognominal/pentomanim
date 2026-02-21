import * as THREE from 'three';
import { PIECE_COLORS } from '../pentomino/colors';
export class PentominoScene {
    constructor(root, box) {
        Object.defineProperty(this, "root", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: root
        });
        Object.defineProperty(this, "box", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: box
        });
        Object.defineProperty(this, "renderer", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "scene", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "camera", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "board", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new THREE.Group()
        });
        Object.defineProperty(this, "placed", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new THREE.Group()
        });
        Object.defineProperty(this, "ghost", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new THREE.Group()
        });
        Object.defineProperty(this, "resizeObserver", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "rafId", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color('#0e1018');
        this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
        this.frameBoard();
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.root.appendChild(this.renderer.domElement);
        const ambient = new THREE.AmbientLight('#ffffff', 0.7);
        const key = new THREE.DirectionalLight('#ffffff', 0.9);
        key.position.set(5, 6, 9);
        this.scene.add(ambient, key, this.board, this.placed, this.ghost);
        this.drawBoardGrid();
        this.resize();
        this.resizeObserver = new ResizeObserver(() => {
            this.resize();
            this.render();
        });
        this.resizeObserver.observe(this.root);
        this.startRenderLoop();
    }
    resize() {
        const w = this.root.clientWidth || 1;
        const h = this.root.clientHeight || 1;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    }
    destroy() {
        this.resizeObserver?.disconnect();
        this.resizeObserver = null;
        if (this.rafId !== null) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }
        this.renderer.dispose();
        this.root.innerHTML = '';
    }
    setPlaced(cells, color = '#5ea2ff') {
        this.placed.clear();
        for (const c of cells) {
            this.placed.add(this.voxel(c, color, 0.95));
        }
        this.render();
    }
    setPlacedByPieces(placements) {
        this.placed.clear();
        for (const placement of placements) {
            const color = PIECE_COLORS[placement.piece] ?? '#5ea2ff';
            for (const cell of placement.cells) {
                this.placed.add(this.voxel(cell, color, 0.95));
            }
        }
        this.render();
    }
    setGhost(cells, valid) {
        this.ghost.clear();
        const color = valid ? '#79d67b' : '#f05d6c';
        for (const c of cells) {
            this.ghost.add(this.voxel(c, color, 0.35));
        }
        this.render();
    }
    voxel([x, y, z], color, opacity) {
        const geo = new THREE.BoxGeometry(0.95, 0.95, 0.95);
        const mat = new THREE.MeshStandardMaterial({
            color,
            transparent: opacity < 1,
            opacity,
        });
        const m = new THREE.Mesh(geo, mat);
        m.position.set(x + 0.5, y + 0.5, z + 0.5);
        return m;
    }
    drawBoardGrid() {
        const [sx, sy, sz] = this.box;
        const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(sx, sy, sz));
        const lines = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: '#8a93ab' }));
        lines.position.set(sx / 2, sy / 2, sz / 2);
        this.board.add(lines);
    }
    frameBoard() {
        const [sx, sy, sz] = this.box;
        const maxDim = Math.max(sx, sy, sz);
        const target = new THREE.Vector3(sx / 2, sy / 2, sz / 2);
        this.camera.position.set(sx * 1.6 + maxDim * 0.5, sy * 1.5 + maxDim * 0.4, sz * 2.3 + maxDim * 1.5);
        this.camera.lookAt(target);
    }
    startRenderLoop() {
        const tick = () => {
            this.renderer.render(this.scene, this.camera);
            this.rafId = requestAnimationFrame(tick);
        };
        tick();
    }
    render() {
        this.renderer.render(this.scene, this.camera);
    }
}
//# sourceMappingURL=scene.js.map