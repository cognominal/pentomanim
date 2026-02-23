<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import type { Vec3 } from '../pentomino/pieces';

  type Props = {
    cells: Vec3[];
    color: string;
    used?: boolean;
  };

  let { cells, color, used = false }: Props = $props();

  let canvas = $state<HTMLCanvasElement | null>(null);
  let resizeObserver: ResizeObserver | null = null;

  function normalize(input: Vec3[]): Vec3[] {
    let minX = Infinity;
    let minY = Infinity;
    let minZ = Infinity;
    for (const [x, y, z] of input) {
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      minZ = Math.min(minZ, z);
    }
    return input.map(([x, y, z]) => [x - minX, y - minY, z - minZ]);
  }

  function shade(hex: string, factor: number): string {
    const raw = hex.replace('#', '');
    const r = Math.max(0, Math.min(255, Math.round(parseInt(raw.slice(0, 2), 16) * factor)));
    const g = Math.max(0, Math.min(255, Math.round(parseInt(raw.slice(2, 4), 16) * factor)));
    const b = Math.max(0, Math.min(255, Math.round(parseInt(raw.slice(4, 6), 16) * factor)));
    const rr = r.toString(16).padStart(2, '0');
    const gg = g.toString(16).padStart(2, '0');
    const bb = b.toString(16).padStart(2, '0');
    return `#${rr}${gg}${bb}`;
  }

  function project(x: number, y: number, z: number, size: number): [number, number] {
    const px = (x - y) * size * 0.9;
    const py = (x + y) * size * 0.45 - z * size * 0.85;
    return [px, py];
  }

  function drawCube(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    z: number,
    size: number,
    base: string,
    alpha: number,
  ): void {
    const [cx, cy] = project(x, y, z, size);

    const top = [
      [cx, cy - size * 0.5],
      [cx + size * 0.9, cy],
      [cx, cy + size * 0.5],
      [cx - size * 0.9, cy],
    ];
    const right = [
      [cx + size * 0.9, cy],
      [cx + size * 0.9, cy + size],
      [cx, cy + size * 1.5],
      [cx, cy + size * 0.5],
    ];
    const left = [
      [cx - size * 0.9, cy],
      [cx, cy + size * 0.5],
      [cx, cy + size * 1.5],
      [cx - size * 0.9, cy + size],
    ];

    ctx.globalAlpha = alpha;

    ctx.fillStyle = shade(base, 1.15);
    ctx.beginPath();
    ctx.moveTo(top[0][0], top[0][1]);
    for (let i = 1; i < top.length; i += 1) {
      ctx.lineTo(top[i][0], top[i][1]);
    }
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = shade(base, 0.85);
    ctx.beginPath();
    ctx.moveTo(right[0][0], right[0][1]);
    for (let i = 1; i < right.length; i += 1) {
      ctx.lineTo(right[i][0], right[i][1]);
    }
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = shade(base, 0.65);
    ctx.beginPath();
    ctx.moveTo(left[0][0], left[0][1]);
    for (let i = 1; i < left.length; i += 1) {
      ctx.lineTo(left[i][0], left[i][1]);
    }
    ctx.closePath();
    ctx.fill();

    ctx.globalAlpha = 1;
  }

  function render(): void {
    if (!canvas) {
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.floor(rect.width));
    const height = Math.max(1, Math.floor(rect.height));
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }

    ctx.clearRect(0, 0, width, height);
    const data = normalize(cells);
    const maxSpan = Math.max(
      1,
      ...data.map(([x, y, z]) => x + y + z),
    );
    const size = Math.max(6, Math.min(14, Math.floor(width / (maxSpan + 6))));

    const pts = data.map(([x, y, z]) => ({
      x,
      y,
      z,
      depth: x + y + z,
    }));
    pts.sort((a, b) => a.depth - b.depth);

    ctx.save();
    ctx.translate(width * 0.5, height * 0.32);
    for (const voxel of pts) {
      drawCube(ctx, voxel.x, voxel.y, voxel.z, size, color, used ? 0.42 : 0.96);
    }
    ctx.restore();
  }

  onMount(() => {
    if (!canvas) {
      return;
    }
    render();
    resizeObserver = new ResizeObserver(() => render());
    resizeObserver.observe(canvas);
    onDestroy(() => {
      resizeObserver?.disconnect();
      resizeObserver = null;
    });
  });

  $effect(() => {
    cells;
    color;
    used;
    render();
  });
</script>

<canvas class="piece-preview" bind:this={canvas}></canvas>

<style>
  .piece-preview {
    width: 100%;
    height: 72px;
    display: block;
    border-radius: 0.5rem;
    background: radial-gradient(circle at 25% 20%, #1f2a42, #121827 75%);
    border: 1px solid #303d5e;
    overflow: hidden;
  }
</style>
