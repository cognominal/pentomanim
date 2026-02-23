import * as THREE from 'three';
import type { Vec3 } from '../pentomino/pieces';
import { PIECE_COLORS } from '../pentomino/colors';

export class PentominoScene {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private board = new THREE.Group();
  private placed = new THREE.Group();
  private ghost = new THREE.Group();
  private resizeObserver: ResizeObserver | null = null;
  private rafId: number | null = null;

  constructor(private root: HTMLElement, private box: Vec3) {
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

  resize(): void {
    const w = this.root.clientWidth || 1;
    const h = this.root.clientHeight || 1;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  destroy(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.renderer.dispose();
    this.root.innerHTML = '';
  }

  setPlaced(cells: Vec3[], color = '#5ea2ff'): void {
    this.placed.clear();
    for (const c of cells) {
      this.placed.add(this.voxel(c, color, 0.95));
    }
    this.render();
  }

  setPlacedByPieces(placements: Array<{ piece: string; cells: Vec3[] }>): void {
    this.placed.clear();
    for (const placement of placements) {
      const color = PIECE_COLORS[placement.piece] ?? '#5ea2ff';
      for (const cell of placement.cells) {
        this.placed.add(this.voxel(cell, color, 0.95));
      }
    }
    this.render();
  }

  setGhost(cells: Vec3[], valid: boolean): void {
    this.ghost.clear();
    const color = valid ? '#79d67b' : '#f05d6c';
    for (const c of cells) {
      this.ghost.add(this.voxel(c, color, 0.35));
    }
    this.render();
  }

  private voxel([x, y, z]: Vec3, color: string, opacity: number): THREE.Mesh {
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

  private drawBoardGrid(): void {
    const [sx, sy, sz] = this.box;
    const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(sx, sy, sz));
    const lines = new THREE.LineSegments(
      edges,
      new THREE.LineBasicMaterial({ color: '#8a93ab' }),
    );
    lines.position.set(sx / 2, sy / 2, sz / 2);
    this.board.add(lines);
  }

  private frameBoard(): void {
    const [sx, sy, sz] = this.box;
    const maxDim = Math.max(sx, sy, sz);
    const target = new THREE.Vector3(sx / 2, sy / 2, sz / 2);
    this.camera.position.set(
      sx * 1.6 + maxDim * 0.5,
      sy * 1.5 + maxDim * 0.4,
      sz * 2.3 + maxDim * 1.5,
    );
    this.camera.lookAt(target);
  }

  private startRenderLoop(): void {
    const tick = (): void => {
      this.renderer.render(this.scene, this.camera);
      this.rafId = requestAnimationFrame(tick);
    };
    tick();
  }

  private render(): void {
    this.renderer.render(this.scene, this.camera);
  }
}
