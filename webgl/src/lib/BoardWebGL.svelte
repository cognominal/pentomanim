<script lang="ts">
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import type { Placement, PieceName } from './pentomino';
  import { PIECE_COLORS, BOARD_COLS, BOARD_ROWS } from './pentomino';

  export let placements: Placement[] = [];
  export let ghost: { name: PieceName; cells: [number, number][]; valid: boolean } | null = null;
  export let settleOutlineCells: [number, number][] = [];
  export let floatingPlacement: { name: PieceName; cells: [number, number][] } | null = null;
  export let maskCells: [number, number][] = [];
  export let interactive = true;
  export let rows = BOARD_ROWS;
  export let cols = BOARD_COLS;

  const dispatch = createEventDispatcher<{
    cellhover: { row: number; col: number } | null;
    cellclick: { row: number; col: number; x: number; y: number };
    celldrop: { row: number; col: number } | null;
    dragstate: { active: boolean };
    pointermove: { row: number; col: number } | null;
  }>();

  let canvas: HTMLCanvasElement;
  let gl: WebGLRenderingContext | null = null;
  let program: WebGLProgram | null = null;
  let posLoc = -1;
  let colorLoc: WebGLUniformLocation | null = null;
  let buffer: WebGLBuffer | null = null;
  let raf = 0;
  let resizeObserver: ResizeObserver | null = null;
  let activePointerId: number | null = null;
  let globalPointerListenersAttached = false;

  function attachGlobalPointerListeners(): void {
    if (globalPointerListenersAttached) {
      return;
    }
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerCancel);
    globalPointerListenersAttached = true;
  }

  function detachGlobalPointerListeners(): void {
    if (!globalPointerListenersAttached) {
      return;
    }
    window.removeEventListener('pointerup', onPointerUp);
    window.removeEventListener('pointercancel', onPointerCancel);
    globalPointerListenersAttached = false;
  }

  function trySetPointerCapture(pointerId: number): void {
    try {
      canvas.setPointerCapture(pointerId);
    } catch {
      // Ignore synthetic/cross-device capture errors; drag can still proceed.
    }
  }

  function tryReleasePointerCapture(pointerId: number): void {
    try {
      if (canvas.hasPointerCapture(pointerId)) {
        canvas.releasePointerCapture(pointerId);
      }
    } catch {
      // Ignore synthetic/cross-device capture errors; finalize drag anyway.
    }
  }

  function hexToRgba(hex: string, alpha = 1): [number, number, number, number] {
    const value = hex.replace('#', '');
    const r = parseInt(value.slice(0, 2), 16) / 255;
    const g = parseInt(value.slice(2, 4), 16) / 255;
    const b = parseInt(value.slice(4, 6), 16) / 255;
    return [r, g, b, alpha];
  }

  function compile(glCtx: WebGLRenderingContext, type: number, source: string): WebGLShader {
    const shader = glCtx.createShader(type);
    if (!shader) {
      throw new Error('Shader allocation failed');
    }
    glCtx.shaderSource(shader, source);
    glCtx.compileShader(shader);
    if (!glCtx.getShaderParameter(shader, glCtx.COMPILE_STATUS)) {
      throw new Error(glCtx.getShaderInfoLog(shader) ?? 'Shader compile failed');
    }
    return shader;
  }

  function setupGL(): void {
    gl = canvas.getContext('webgl', { antialias: true, alpha: true });
    if (!gl) {
      return;
    }

    const vs = compile(
      gl,
      gl.VERTEX_SHADER,
      'attribute vec2 aPos;\nvoid main(){ gl_Position = vec4(aPos, 0.0, 1.0); }',
    );
    const fs = compile(
      gl,
      gl.FRAGMENT_SHADER,
      'precision mediump float;\nuniform vec4 uColor;\nvoid main(){ gl_FragColor = uColor; }',
    );

    program = gl.createProgram();
    if (!program) {
      return;
    }
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) ?? 'Program link failed');
    }

    posLoc = gl.getAttribLocation(program, 'aPos');
    colorLoc = gl.getUniformLocation(program, 'uColor');
    buffer = gl.createBuffer();

    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  }

  function scheduleDraw(): void {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(draw);
  }

  function addRect(vertices: number[], row: number, col: number): void {
    const x1 = -1 + (2 * col) / cols;
    const x2 = -1 + (2 * (col + 1)) / cols;
    const y1 = 1 - (2 * row) / rows;
    const y2 = 1 - (2 * (row + 1)) / rows;
    vertices.push(x1, y1, x2, y1, x1, y2, x2, y1, x2, y2, x1, y2);
  }

  function drawBatch(cells: [number, number][], color: [number, number, number, number]): void {
    if (!gl || !buffer || !colorLoc) {
      return;
    }
    const vertices: number[] = [];
    for (const [row, col] of cells) {
      addRect(vertices, row, col);
    }
    if (!vertices.length) {
      return;
    }
    gl.uniform4f(colorLoc, color[0], color[1], color[2], color[3]);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STREAM_DRAW);
    gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 2);
  }

  function drawGrid(): void {
    if (!gl || !colorLoc || !buffer) {
      return;
    }
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        drawBatch([[r, c]], [0.05, 0.06, 0.1, 1]);
      }
    }
  }

  function buildOccupancy(): Map<string, PieceName> {
    const map = new Map<string, PieceName>();
    for (const placement of placements) {
      for (const [r, c] of placement.cells) {
        map.set(`${r},${c}`, placement.name);
      }
    }
    return map;
  }

  function addHSegment(vertices: number[], row: number, col: number, thickness: number): void {
    const x1 = -1 + (2 * col) / cols;
    const x2 = -1 + (2 * (col + 1)) / cols;
    const y = 1 - (2 * row) / rows;
    const yTop = y + thickness;
    const yBottom = y - thickness;
    vertices.push(x1, yTop, x2, yTop, x1, yBottom, x2, yTop, x2, yBottom, x1, yBottom);
  }

  function addVSegment(vertices: number[], row: number, col: number, thickness: number): void {
    const x = -1 + (2 * col) / cols;
    const y1 = 1 - (2 * row) / rows;
    const y2 = 1 - (2 * (row + 1)) / rows;
    const xL = x - thickness;
    const xR = x + thickness;
    vertices.push(xL, y1, xR, y1, xL, y2, xR, y1, xR, y2, xL, y2);
  }

  function drawPieceBoundaries(): void {
    if (!gl || !colorLoc || !buffer) {
      return;
    }
    const occupied = buildOccupancy();
    if (occupied.size === 0) {
      return;
    }

    const edgeColor: [number, number, number, number] = [0.08, 0.1, 0.16, 0.95];
    const thicknessH = Math.max(0.005, 0.02 / rows);
    const thicknessV = Math.max(0.005, 0.02 / cols);
    const vertices: number[] = [];

    for (const [key, name] of occupied) {
      const [r, c] = key.split(',').map(Number);

      const top = occupied.get(`${r - 1},${c}`);
      if (top !== name) {
        addHSegment(vertices, r, c, thicknessH);
      }

      const bottom = occupied.get(`${r + 1},${c}`);
      if (bottom !== name) {
        addHSegment(vertices, r + 1, c, thicknessH);
      }

      const left = occupied.get(`${r},${c - 1}`);
      if (left !== name) {
        addVSegment(vertices, r, c, thicknessV);
      }

      const right = occupied.get(`${r},${c + 1}`);
      if (right !== name) {
        addVSegment(vertices, r, c + 1, thicknessV);
      }
    }

    if (vertices.length === 0) {
      return;
    }
    gl.uniform4f(colorLoc, edgeColor[0], edgeColor[1], edgeColor[2], edgeColor[3]);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STREAM_DRAW);
    gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 2);
  }

  function drawCellsOutline(
    cells: [number, number][],
    color: [number, number, number, number],
  ): void {
    if (!gl || !colorLoc || !buffer || cells.length === 0) {
      return;
    }
    const occupied = new Set(cells.map(([r, c]) => `${r},${c}`));
    const thicknessH = Math.max(0.005, 0.02 / rows);
    const thicknessV = Math.max(0.005, 0.02 / cols);
    const vertices: number[] = [];

    for (const [r, c] of cells) {
      if (!occupied.has(`${r - 1},${c}`)) {
        addHSegment(vertices, r, c, thicknessH);
      }
      if (!occupied.has(`${r + 1},${c}`)) {
        addHSegment(vertices, r + 1, c, thicknessH);
      }
      if (!occupied.has(`${r},${c - 1}`)) {
        addVSegment(vertices, r, c, thicknessV);
      }
      if (!occupied.has(`${r},${c + 1}`)) {
        addVSegment(vertices, r, c + 1, thicknessV);
      }
    }

    if (vertices.length === 0) {
      return;
    }
    gl.uniform4f(colorLoc, color[0], color[1], color[2], color[3]);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STREAM_DRAW);
    gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 2);
  }

  function draw(): void {
    if (!gl || !program || !buffer) {
      return;
    }
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.02, 0.03, 0.06, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(program);
    drawGrid();
    if (maskCells.length > 0) {
      drawBatch(maskCells, [0.16, 0.2, 0.35, 0.65]);
    }

    for (const p of placements) {
      drawBatch(p.cells, hexToRgba(PIECE_COLORS[p.name], 0.9));
    }
    if (floatingPlacement) {
      drawBatch(floatingPlacement.cells, hexToRgba(PIECE_COLORS[floatingPlacement.name], 0.9));
    }
    drawPieceBoundaries();
    drawCellsOutline(settleOutlineCells, [0.7, 0.72, 0.76, 0.48]);
    if (ghost) {
      const tint = ghost.valid ? '#9ef01a' : '#ef233c';
      drawBatch(ghost.cells, hexToRgba(tint, 0.32));
    }
  }

  function pointerToCell(event: PointerEvent): { row: number; col: number } | null {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
      return null;
    }
    const col = Math.floor((x / rect.width) * cols);
    const row = Math.floor((y / rect.height) * rows);
    if (row < 0 || col < 0 || row >= rows || col >= cols) {
      return null;
    }
    return { row, col };
  }

  function pointerToBoardPos(
    event: PointerEvent,
    clampToBoard: boolean,
  ): { row: number; col: number } | null {
    const rect = canvas.getBoundingClientRect();
    let x = event.clientX - rect.left;
    let y = event.clientY - rect.top;
    if (clampToBoard) {
      x = Math.max(0, Math.min(rect.width, x));
      y = Math.max(0, Math.min(rect.height, y));
    }
    if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
      return null;
    }
    return {
      row: (y / rect.height) * rows,
      col: (x / rect.width) * cols,
    };
  }

  function onMove(event: PointerEvent): void {
    if (!interactive) {
      return;
    }
    const clamp = activePointerId !== null;
    dispatch('pointermove', pointerToBoardPos(event, clamp));
    dispatch('cellhover', pointerToCell(event));
  }

  function onLeave(): void {
    if (!interactive) {
      return;
    }
    dispatch('cellhover', null);
  }

  function onPointerDown(event: PointerEvent): void {
    if (!interactive) {
      return;
    }
    const cell = pointerToCell(event);
    if (!cell) {
      return;
    }
    activePointerId = event.pointerId;
    trySetPointerCapture(event.pointerId);
    attachGlobalPointerListeners();
    dispatch('dragstate', { active: true });
    dispatch('pointermove', pointerToBoardPos(event, true));
    dispatch('cellhover', cell);
    dispatch('cellclick', { ...cell, x: event.clientX, y: event.clientY });
  }

  function onPointerUp(event: PointerEvent): void {
    if (!interactive || activePointerId === null) {
      return;
    }
    const matchesPointer = event.pointerId === activePointerId || event.pointerId === 0;
    if (!matchesPointer) {
      return;
    }
    const pointerId = activePointerId;
    activePointerId = null;
    detachGlobalPointerListeners();
    tryReleasePointerCapture(pointerId);
    dispatch('dragstate', { active: false });
    dispatch('pointermove', pointerToBoardPos(event, true));
    dispatch('celldrop', pointerToCell(event));
  }

  function onPointerCancel(event: PointerEvent): void {
    if (activePointerId === null) {
      return;
    }
    const matchesPointer = event.pointerId === activePointerId || event.pointerId === 0;
    if (!matchesPointer) {
      return;
    }
    const pointerId = activePointerId;
    activePointerId = null;
    detachGlobalPointerListeners();
    tryReleasePointerCapture(pointerId);
    dispatch('dragstate', { active: false });
    dispatch('pointermove', null);
    dispatch('celldrop', null);
  }

  function resizeCanvas(): void {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    scheduleDraw();
  }

  onMount(() => {
    setupGL();
    resizeCanvas();
    resizeObserver = new ResizeObserver(() => resizeCanvas());
    resizeObserver.observe(canvas);
    scheduleDraw();
  });

  onDestroy(() => {
    cancelAnimationFrame(raf);
    resizeObserver?.disconnect();
    activePointerId = null;
    detachGlobalPointerListeners();
  });

  $: {
    placements;
    ghost;
    maskCells;
    settleOutlineCells;
    floatingPlacement;
    rows;
    cols;
    scheduleDraw();
  }
</script>

<canvas
  bind:this={canvas}
  class:interactive
  on:pointerdown={onPointerDown}
  on:pointerup={onPointerUp}
  on:pointercancel={onPointerCancel}
  on:pointermove={onMove}
  on:pointerleave={onLeave}
/>

<style>
  canvas {
    width: 100%;
    height: 100%;
    border-radius: 0;
    display: block;
    background: #05070f;
    touch-action: none;
  }

  .interactive {
    cursor: crosshair;
  }

  canvas:not(.interactive) {
    pointer-events: none;
  }
</style>
