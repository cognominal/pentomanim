<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import type { SolveTraceEvent, SolverResponse } from '../pentomino/messages';
  import type { Placement3D } from '../pentomino/placement-gen';
  import { PIECE_COLORS } from '../pentomino/colors';
  import { PIECE_ORDER, PIECES_3D } from '../pentomino/pieces';
  import type { Vec3 } from '../pentomino/pieces';
  import PiecePreview3D from '../three/PiecePreview3D.svelte';
  import { PentominoScene } from '../three/scene';

  let host = $state<HTMLElement | null>(null);
  let scene = $state<PentominoScene | null>(null);
  let worker = $state<Worker | null>(null);
  let status = $state('Idle');
  let placed = $state<number[]>([]);
  let renderedPieces = $state(0);
  let renderedCells = $state(0);
  let animationTimer = $state<ReturnType<typeof setInterval> | null>(null);
  let animationRunning = $state(false);
  let animationStep = $state(0);
  let animationStepsTotal = $state(0);
  let previewCellsByPiece = $state<Record<string, Vec3[]>>({});
  let placedPieceNames = $state<Set<string>>(new Set());
  let sliceView = $state<string[][][]>([]);

  const box = { x: 5, y: 4, z: 3 };
  const pieceNames = PIECE_ORDER;
  const BASE_CELLS_BY_PIECE: Record<string, Vec3[]> = Object.fromEntries(
    PIECES_3D.map((piece) => [piece.name, piece.cells]),
  );

  function normalizeCells(cells: Vec3[]): Vec3[] {
    let minX = Infinity;
    let minY = Infinity;
    let minZ = Infinity;
    for (const [x, y, z] of cells) {
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      minZ = Math.min(minZ, z);
    }
    return cells.map(([x, y, z]) => [x - minX, y - minY, z - minZ]);
  }

  function buildPreviewMap(activePlacements: Placement3D[]): Record<string, Vec3[]> {
    const map: Record<string, Vec3[]> = {};
    for (const name of pieceNames) {
      map[name] = BASE_CELLS_BY_PIECE[name];
    }
    for (const placement of activePlacements) {
      map[placement.piece] = normalizeCells(placement.cells);
    }
    return map;
  }

  function syncSceneAndPicker(activePlacements: Placement3D[]): void {
    scene?.setPlacedByPieces(activePlacements);
    scene?.setGhost([], true);
    previewCellsByPiece = buildPreviewMap(activePlacements);
    placedPieceNames = new Set(activePlacements.map((p) => p.piece));
    sliceView = buildSliceView(activePlacements);
    renderedPieces = activePlacements.length;
    renderedCells = activePlacements.reduce(
      (sum, placement) => sum + placement.cells.length,
      0,
    );
  }

  function buildSliceView(activePlacements: Placement3D[]): string[][][] {
    const layers: string[][][] = [];
    for (let z = 0; z < box.z; z += 1) {
      const rows: string[][] = [];
      for (let y = 0; y < box.y; y += 1) {
        rows.push(Array.from({ length: box.x }, () => ''));
      }
      layers.push(rows);
    }
    for (const placement of activePlacements) {
      for (const [x, y, z] of placement.cells) {
        if (
          z >= 0 && z < box.z &&
          y >= 0 && y < box.y &&
          x >= 0 && x < box.x
        ) {
          const row = box.y - 1 - y;
          layers[z][row][x] = placement.piece;
        }
      }
    }
    return layers;
  }

  function initSolver(): void {
    stopAnimation();
    placed = [];
    animationStep = 0;
    animationStepsTotal = 0;
    syncSceneAndPicker([]);
    worker?.postMessage({ type: 'init', box });
  }

  function askHint(): void {
    worker?.postMessage({ type: 'hint', placedIds: [...placed] });
  }

  function solveNow(): void {
    stopAnimation();
    worker?.postMessage({ type: 'solve', placedIds: [...placed], maxSolutions: 1 });
  }

  function stopAnimation(): void {
    if (!animationTimer) {
      return;
    }
    clearInterval(animationTimer);
    animationTimer = null;
    animationRunning = false;
  }

  function animateSolve(): void {
    if (animationRunning) {
      stopAnimation();
      status = 'Animation stopped.';
      return;
    }
    worker?.postMessage({
      type: 'animate-solve',
      placedIds: [...placed],
      maxSolutions: 1,
      maxTraceEvents: 20_000,
    });
  }

  function applyHint(placement: Placement3D | null): void {
    if (!placement) {
      status = 'No hint available from this state.';
      return;
    }
    scene?.setGhost(placement.cells, true);
    status = `Hint: place ${placement.piece} (id ${placement.id}).`;
  }

  function playTrace(
    seedPlacements: Placement3D[],
    trace: SolveTraceEvent[],
    firstPlacementSet: Placement3D[],
  ): void {
    stopAnimation();
    const active = new Map<number, Placement3D>();
    for (const placement of seedPlacements) {
      active.set(placement.id, placement);
    }

    syncSceneAndPicker([...active.values()]);
    animationRunning = true;
    animationStep = 0;
    animationStepsTotal = trace.length;
    status = `Animating search (${trace.length} events)...`;

    animationTimer = setInterval(() => {
      if (animationStep >= trace.length) {
        stopAnimation();
        placed = firstPlacementSet.map((placement) => placement.id);
        syncSceneAndPicker(firstPlacementSet);
        status = 'Animation complete.';
        return;
      }
      const event = trace[animationStep];
      if (event.type === 'place') {
        active.set(event.placement.id, event.placement);
      } else {
        active.delete(event.placement.id);
      }
      syncSceneAndPicker([...active.values()]);
      animationStep += 1;
    }, 70);
  }

  onMount(() => {
    if (!host) {
      return;
    }
    scene = new PentominoScene(host, [box.x, box.y, box.z]);
    syncSceneAndPicker([]);

    worker = new Worker(new URL('../pentomino/solver.worker.ts', import.meta.url), {
      type: 'module',
    });

    worker.onmessage = (event: MessageEvent<SolverResponse>) => {
      const data = event.data;
      if (data.type === 'ready') {
        status = `Ready. ${data.placements} legal placements generated.`;
      } else if (data.type === 'hint') {
        applyHint(data.placement);
      } else if (data.type === 'solved') {
        if (data.firstPlacementSet.length === 0) {
          status = 'No solution from this state.';
          return;
        }
        placed = data.firstPlacementSet.map((placement) => placement.id);
        syncSceneAndPicker(data.firstPlacementSet);
        status = `Solve complete. ${data.firstPlacementSet.length} pieces placed.`;
      } else if (data.type === 'solve-trace') {
        if (!data.firstPlacementSet.length) {
          status = 'No solution from this state.';
          return;
        }
        playTrace(data.seedPlacements, data.trace, data.firstPlacementSet);
      } else {
        status = data.message;
      }
    };

    initSolver();

    const onResize = (): void => scene?.resize();
    window.addEventListener('resize', onResize);
    onDestroy(() => {
      stopAnimation();
      window.removeEventListener('resize', onResize);
      worker?.terminate();
      scene?.destroy();
    });
  });
</script>

<section class="shell">
  <header>
    <h2>3D Pentomino (3x4x5) Prototype</h2>
    <p>{status}</p>
    <p>Rendered: {renderedPieces} pieces, {renderedCells} cells.</p>
    {#if animationRunning}
      <p>Search steps: {animationStep}/{animationStepsTotal}</p>
    {/if}
  </header>

  <div class="controls">
    <button onclick={initSolver}>Init</button>
    <button onclick={askHint}>Hint</button>
    <button onclick={solveNow}>Solve</button>
    <button onclick={animateSolve}>
      {animationRunning ? 'Stop Animation' : 'Animate Solve'}
    </button>
  </div>

  <div class="workspace">
    <div class="viewport" bind:this={host}></div>

    <aside class="slices" aria-label="2D slices">
      <h3>Board Slices</h3>
      <div class="slice-stack">
        {#each sliceView as layer, z}
          <section class="slice-layer">
            <header>z = {z + 1}</header>
            <div class="slice-grid">
              {#each layer as row}
                {#each row as piece}
                  <div
                    class="slice-cell"
                    style={`--cell-color: ${piece ? PIECE_COLORS[piece] : '#182034'}`}
                    title={piece ? `Piece ${piece}` : 'Empty'}
                  >
                    {piece}
                  </div>
                {/each}
              {/each}
            </div>
          </section>
        {/each}
      </div>
    </aside>

    <aside class="picker" aria-label="3D piece picker">
      <h3>Picker</h3>
      <div class="picker-grid">
        {#each pieceNames as name}
          {@const used = placedPieceNames.has(name)}
          <div class="piece-card" class:used={used}>
            <div class="piece-meta">
              <strong>{name}</strong>
              <span>{used ? 'Placed' : 'Available'}</span>
            </div>
            <PiecePreview3D
              cells={previewCellsByPiece[name] ?? BASE_CELLS_BY_PIECE[name]}
              color={PIECE_COLORS[name]}
              {used}
            />
          </div>
        {/each}
      </div>
    </aside>
  </div>
</section>

<style>
  .shell {
    display: grid;
    grid-template-rows: auto auto auto;
    gap: 0.75rem;
    padding: 0.75rem;
    border: 1px solid #2a3240;
    border-radius: 0.75rem;
    background: #141925;
    color: #e9eefb;
  }

  .controls {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .controls button {
    border: 1px solid #4f6385;
    background: #23314d;
    color: #e9eefb;
    border-radius: 0.5rem;
    padding: 0.35rem 0.7rem;
    cursor: pointer;
  }

  .workspace {
    display: grid;
    align-items: stretch;
    gap: 0.75rem;
    grid-template-columns:
      minmax(0, 1fr)
      minmax(220px, 260px)
      minmax(230px, 280px);
    min-height: 340px;
    height: min(62dvh, 720px);
    overflow: clip;
  }

  .viewport {
    width: 100%;
    min-height: 340px;
    height: 100%;
    border-radius: 0.6rem;
    overflow: hidden;
    border: 1px solid #2b3342;
  }

  .slices {
    border: 1px solid #2b3342;
    border-radius: 0.6rem;
    padding: 0.55rem;
    background: #111724;
    min-height: 340px;
    height: 100%;
    overflow: auto;
  }

  .slices h3 {
    margin: 0 0 0.5rem;
    font-size: 0.95rem;
  }

  .slice-stack {
    display: grid;
    gap: 0.5rem;
  }

  .slice-layer {
    border: 1px solid #33405f;
    border-radius: 0.5rem;
    background: #1b2338;
    padding: 0.35rem;
    display: grid;
    gap: 0.3rem;
  }

  .slice-layer header {
    font-size: 0.72rem;
    color: #b7c4e4;
  }

  .slice-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.2rem;
  }

  .slice-cell {
    border-radius: 0.25rem;
    border: 1px solid #2e3a59;
    background: color-mix(in srgb, var(--cell-color) 70%, #101624 30%);
    color: #f4f7ff;
    text-align: center;
    font-size: 0.65rem;
    line-height: 1;
    height: 1.35rem;
    display: grid;
    place-items: center;
    font-weight: 700;
  }

  .picker {
    border: 1px solid #2b3342;
    border-radius: 0.6rem;
    padding: 0.55rem;
    background: #111724;
    min-height: 340px;
    height: 100%;
    overflow: auto;
  }

  .picker h3 {
    margin: 0 0 0.5rem;
    font-size: 0.95rem;
  }

  .picker-grid {
    display: grid;
    gap: 0.45rem;
  }

  .piece-card {
    display: grid;
    gap: 0.3rem;
    padding: 0.35rem;
    border: 1px solid #354361;
    border-radius: 0.55rem;
    background: #182238;
    transition: transform 150ms ease, opacity 150ms ease;
  }

  .piece-card.used {
    opacity: 0.62;
    transform: scale(0.98);
  }

  .piece-meta {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 0.3rem;
  }

  .piece-meta span {
    font-size: 0.72rem;
    color: #a9b7d6;
  }

  @media (max-width: 980px) {
    .workspace {
      grid-template-columns: 1fr;
      grid-template-rows:
        minmax(220px, 1fr)
        minmax(170px, auto)
        minmax(160px, auto);
      height: auto;
    }

    .slices {
      min-height: 170px;
      max-height: 36dvh;
    }

    .picker {
      min-height: 160px;
      max-height: 38dvh;
    }
  }
</style>
