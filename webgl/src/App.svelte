<script lang="ts">
  import { onDestroy } from 'svelte';
  import BoardWebGL from './lib/BoardWebGL.svelte';
  import {
    PIECE_COLORS,
    PIECE_ORDER,
    PIECES,
    cellsForPose,
    inBounds,
    placeAtAnchor,
    solutionKey,
  } from './lib/pentomino';
  import type { Placement, PieceName, Pose } from './lib/pentomino';
  import { canApplyPlacement, solveFromPlacements, solveWithTraceFromPlacements } from './lib/solver';
  import type { TraceEvent } from './lib/solver';

  type Hover = { row: number; col: number } | null;

  const isTouchDevice =
    typeof window !== 'undefined' &&
    ('ontouchstart' in window ||
      window.matchMedia?.('(pointer: coarse)').matches ||
      navigator.maxTouchPoints > 0);
  const repoUrl = 'https://github.com/cognominal/pentomanim';

  let selectedPiece: PieceName | null = 'F';
  let pose: Pose = { rotation: 0, flipped: false };
  let hover: Hover = null;
  let placements: Placement[] = [];
  let prefixCount = 0;
  let solvedSolutions: Placement[][] = [];
  let status = isTouchDevice
    ? 'Pick a piece and tap the board to place it.'
    : 'Pick a piece and click the board to place it.';
  let isAnimating = false;
  let animationTimer: ReturnType<typeof setInterval> | null = null;
  let animationStepsUsed = 0;
  let speedSlider = 0;
  let showRepoLink = false;
  const MIN_INITIAL_SPEED = 0.01;
  const MAX_INITIAL_SPEED = 1000000;
  const SPEED_EXP_RANGE = Math.log2(MAX_INITIAL_SPEED / MIN_INITIAL_SPEED);
  $: initialSpeedMultiplier = MIN_INITIAL_SPEED * 2 ** ((speedSlider / 100) * SPEED_EXP_RANGE);

  $: visiblePlacements = placements.slice(0, prefixCount);
  $: usedNames = new Set(visiblePlacements.map((p) => p.name));
  $: availablePieces = PIECE_ORDER.filter((name) => !usedNames.has(name));
  $: if (selectedPiece && usedNames.has(selectedPiece)) {
    selectedPiece = availablePieces[0] ?? null;
  }

  $: transformed = selectedPiece ? cellsForPose(selectedPiece, pose) : null;
  $: ghostPlacement =
    selectedPiece && transformed && hover
      ? {
          name: selectedPiece,
          cells: placeAtAnchor(transformed, hover.row, hover.col),
        }
      : null;

  $: ghostValid =
    ghostPlacement !== null &&
    inBounds(ghostPlacement.cells) &&
    canApplyPlacement(visiblePlacements, ghostPlacement as Placement);

  function rotateRight(): void {
    pose = { ...pose, rotation: ((pose.rotation + 1) % 4) as Pose['rotation'] };
  }

  function rotateLeft(): void {
    pose = { ...pose, rotation: ((pose.rotation + 3) % 4) as Pose['rotation'] };
  }

  function flipPiece(): void {
    pose = { ...pose, flipped: !pose.flipped };
  }

  function resetPose(): void {
    pose = { rotation: 0, flipped: false };
  }

  function selectPiece(name: PieceName): void {
    if (isAnimating) {
      return;
    }
    selectedPiece = name;
    resetPose();
  }

  function truncateToPrefix(): void {
    if (prefixCount < placements.length) {
      placements = placements.slice(0, prefixCount);
    }
  }

  function addSolved(solution: Placement[]): void {
    if (solution.length !== PIECE_ORDER.length) {
      return;
    }
    const key = solutionKey(solution);
    if (!solvedSolutions.some((s) => solutionKey(s) === key)) {
      solvedSolutions = [clonePlacements(solution), ...solvedSolutions];
    }
  }

  function clonePlacements(data: Placement[]): Placement[] {
    return data.map((p) => ({
      name: p.name,
      cells: p.cells.map(([r, c]) => [r, c] as [number, number]),
    }));
  }

  function clearSolverAfterSolved(message: string): void {
    placements = [];
    prefixCount = 0;
    hover = null;
    selectedPiece = 'F';
    resetPose();
    status = message;
  }

  function commitPlacement(candidate: Placement): void {
    if (isAnimating) {
      return;
    }
    if (!inBounds(candidate.cells) || !canApplyPlacement(visiblePlacements, candidate)) {
      return;
    }
    truncateToPrefix();
    placements = [...placements, clonePlacements([candidate])[0]];
    prefixCount = placements.length;
    status = `${candidate.name} placed.`;

    if (placements.length === PIECE_ORDER.length) {
      addSolved(placements);
      clearSolverAfterSolved('Rectangle solved manually. Added to Solved; Solver cleared.');
    }
  }

  function placementAtCell(row: number, col: number): Placement | null {
    if (!selectedPiece || !transformed) {
      return null;
    }
    return {
      name: selectedPiece,
      cells: placeAtAnchor(transformed, row, col),
    };
  }

  function removePieceAt(row: number, col: number): boolean {
    if (isAnimating) {
      return false;
    }
    const hit = visiblePlacements.find((p) => p.cells.some(([r, c]) => r === row && c === col));
    if (!hit) {
      return false;
    }
    placements = visiblePlacements.filter((p) => p.name !== hit.name);
    prefixCount = placements.length;
    selectedPiece = hit.name;
    resetPose();
    hover = null;
    status = `${hit.name} removed and selected.`;
    return true;
  }

  function onBoardClick(event: CustomEvent<{ row: number; col: number }>): void {
    if (isAnimating) {
      return;
    }
    const { row, col } = event.detail;
    hover = { row, col };
    if (removePieceAt(row, col)) {
      return;
    }
    const candidate = placementAtCell(row, col);
    if (!candidate) {
      return;
    }
    commitPlacement(candidate);
  }

  function solveNow(): void {
    if (isAnimating) {
      return;
    }
    animationStepsUsed = 0;
    const start = clonePlacements(visiblePlacements);
    const solved = solveFromPlacements(start);
    if (!solved) {
      status = 'No completion found from the current prefix.';
      return;
    }
    const snapshot = clonePlacements(solved);
    addSolved(snapshot);
    clearSolverAfterSolved('Solved from current state. Added to Solved; Solver cleared.');
  }

  function importSolved(index: number): void {
    if (isAnimating) {
      return;
    }
    const chosen = solvedSolutions[index];
    placements = clonePlacements(chosen);
    prefixCount = placements.length;
    selectedPiece = null;
    status = `Loaded solved rectangle #${index + 1} into Solver.`;
  }

  function onKey(event: KeyboardEvent): void {
    if (isAnimating) {
      return;
    }
    const keyUpper = event.key.toUpperCase();
    if (PIECE_ORDER.includes(keyUpper as PieceName)) {
      const piece = keyUpper as PieceName;
      if (!usedNames.has(piece)) {
        selectPiece(piece);
      }
      return;
    }

    if (!selectedPiece) {
      return;
    }
    if (event.key === 'r' && event.shiftKey) {
      rotateLeft();
      return;
    }
    if (event.key.toLowerCase() === 'r') {
      rotateRight();
      return;
    }
    if (event.key.toLowerCase() === 'x') {
      flipPiece();
      return;
    }
    if (event.key === 'Escape') {
      hover = null;
    }
  }

  function toggleRepoLink(): void {
    showRepoLink = !showRepoLink;
  }

  function closeRepoLinkOnOutsideClick(event: MouseEvent): void {
    if (!showRepoLink) {
      return;
    }
    const target = event.target as HTMLElement | null;
    if (!target || !target.closest('.repo-toggle')) {
      showRepoLink = false;
    }
  }

  function onBoardHover(event: CustomEvent<{ row: number; col: number } | null>): void {
    if (isAnimating) {
      return;
    }
    hover = event.detail;
  }

  function sliderChanged(value: number): void {
    prefixCount = Math.max(0, Math.min(value, placements.length));
    status = `${prefixCount} pentominoes fixed in Solver.`;
  }

  function onSliderInput(event: Event): void {
    if (isAnimating) {
      return;
    }
    const target = event.currentTarget as HTMLInputElement;
    sliderChanged(Number(target.value));
  }

  function onInitialSpeedInput(event: Event): void {
    if (isAnimating) {
      return;
    }
    const target = event.currentTarget as HTMLInputElement;
    speedSlider = Number(target.value);
  }

  function applyTraceEvent(snapshot: Placement[], event: TraceEvent): Placement[] {
    if (event.type === 'place') {
      return [...snapshot, clonePlacements([event.placement])[0]];
    }
    return snapshot.filter((p) => p.name !== event.placement.name);
  }

  function stopAnimationTimer(): void {
    if (animationTimer) {
      clearInterval(animationTimer);
      animationTimer = null;
    }
  }

  function animateSolve(): void {
    if (isAnimating) {
      return;
    }

    const start = clonePlacements(visiblePlacements);
    animationStepsUsed = 0;
    const traced = solveWithTraceFromPlacements(start, 200000);
    let solution: Placement[];
    let trace: TraceEvent[];

    if (!traced) {
      const solved = solveFromPlacements(start);
      if (!solved) {
        status = 'No completion found from the current prefix.';
        return;
      }
      const solvedSnapshot = clonePlacements(solved);
      const startNames = new Set(start.map((p) => p.name));
      trace = solvedSnapshot
        .filter((p) => !startNames.has(p.name))
        .map((placement) => ({ type: 'place' as const, placement }));
      solution = solvedSnapshot;
      status = 'Trace was too long; using direct completion animation (no backtracking).';
    } else {
      ({ solution, trace } = traced);
    }

    if (trace.length === 0) {
      addSolved(solution);
      clearSolverAfterSolved('Already solved. Added to Solved; Solver cleared.');
      return;
    }

    isAnimating = true;
    selectedPiece = null;
    hover = null;
    status = `Animating solve: 0/${trace.length} steps`;

    let cursor = 0;
    let working = clonePlacements(start);
    const startedAt = Date.now();
    let stepBudget = 0;

    stopAnimationTimer();
    animationTimer = setInterval(() => {
      const elapsedMs = Date.now() - startedAt;
      const speedFactor = initialSpeedMultiplier * 2 ** (elapsedMs / 5000);
      stepBudget += speedFactor;
      const stepsThisTick = Math.floor(stepBudget);
      if (stepsThisTick <= 0) {
        status = `Animating solve: ${cursor}/${trace.length} steps (${speedFactor.toFixed(2)}x speed)`;
        return;
      }
      stepBudget -= stepsThisTick;

      let consumed = 0;
      while (consumed < stepsThisTick && cursor < trace.length) {
        const step = trace[cursor];
        working = applyTraceEvent(working, step);
        cursor += 1;
        consumed += 1;
        // Keep some remove visibility at low speed, but don't throttle high-speed playback.
        if (step.type === 'remove' && stepsThisTick <= 2) {
          break;
        }
      }
      placements = clonePlacements(working);
      prefixCount = placements.length;
      animationStepsUsed = cursor;
      status = `Animating solve: ${cursor}/${trace.length} steps (${speedFactor.toFixed(2)}x speed)`;

      if (cursor >= trace.length) {
        stopAnimationTimer();
        isAnimating = false;
        addSolved(solution);
        clearSolverAfterSolved('Animated solve complete. Added to Solved; Solver cleared.');
      }
    }, 100);
  }

  onDestroy(() => {
    stopAnimationTimer();
  });

  function pieceCells(name: PieceName): [number, number][] {
    return PIECES[name];
  }

  function bounds(cells: [number, number][]): { rows: number; cols: number } {
    const maxR = Math.max(...cells.map((c) => c[0])) + 1;
    const maxC = Math.max(...cells.map((c) => c[1])) + 1;
    return { rows: maxR, cols: maxC };
  }
</script>

<svelte:window on:keydown={onKey} on:click={closeRepoLinkOnOutsideClick} />

<main>
  {#if !isTouchDevice}
    <div class="repo-toggle">
      <button
        class="repo-icon-btn"
        class:active={showRepoLink}
        on:click={toggleRepoLink}
        aria-label="Toggle GitHub repo link"
        title="Project repository"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            fill="currentColor"
            d="M12 .5C5.65.5.5 5.68.5 12.07c0 5.1 3.3 9.42 7.88 10.95.58.1.79-.26.79-.57l-.02-2.03c-3.2.7-3.88-1.55-3.88-1.55-.53-1.34-1.28-1.7-1.28-1.7-1.05-.72.08-.7.08-.7 1.15.08 1.76 1.2 1.76 1.2 1.03 1.77 2.7 1.26 3.36.97.1-.75.4-1.26.72-1.54-2.55-.3-5.23-1.28-5.23-5.72 0-1.26.44-2.3 1.17-3.1-.12-.3-.5-1.5.11-3.12 0 0 .96-.31 3.14 1.2a10.77 10.77 0 0 1 5.72 0c2.18-1.51 3.14-1.2 3.14-1.2.61 1.62.23 2.82.11 3.12.73.8 1.17 1.84 1.17 3.1 0 4.45-2.68 5.41-5.24 5.7.41.35.78 1.06.78 2.15l-.02 3.19c0 .32.21.68.8.57A11.6 11.6 0 0 0 23.5 12.07C23.5 5.68 18.35.5 12 .5Z"
          />
        </svg>
      </button>
      {#if showRepoLink}
        <div class="repo-popover">
          <a href={repoUrl} target="_blank" rel="noopener noreferrer">{repoUrl}</a>
        </div>
      {/if}
    </div>
  {/if}

  <section class="pane solver-pane">
    <header>
      <h2>Solver</h2>
      <p>{status}</p>
    </header>

    <div class="piece-bank">
      {#each PIECE_ORDER as name}
        {@const disabled = usedNames.has(name)}
        {@const shape = pieceCells(name)}
        {@const dims = bounds(shape)}
        <button
          class="piece-btn"
          class:selected={selectedPiece === name}
          class:used={disabled}
          on:click={() => selectPiece(name)}
          disabled={disabled || isAnimating}
          aria-label={`Select ${name}`}
        >
          <span class="label">{name}</span>
          <span
            class="mini"
            style={`--rows:${dims.rows};--cols:${dims.cols};--c:${PIECE_COLORS[name]}`}
          >
            {#each shape as [r, c]}
              <span class="cell" style={`grid-row:${r + 1};grid-column:${c + 1}`}></span>
            {/each}
          </span>
        </button>
      {/each}
    </div>

    <div class="toolbar">
      <button on:click={rotateLeft} disabled={!selectedPiece}>Rotate ⟲</button>
      <button on:click={rotateRight} disabled={!selectedPiece}>Rotate ⟳</button>
      <button on:click={flipPiece} disabled={!selectedPiece}>Flip ↔</button>
      <button on:click={resetPose} disabled={!selectedPiece}>Reset</button>
      <button class="solve" on:click={solveNow} disabled={isAnimating}>Solve</button>
      <button class="solve" on:click={animateSolve} disabled={isAnimating}>Animate Solve</button>
      <span class="pose-readout">steps used: {animationStepsUsed}</span>
      <span class="pose-readout">
        {#if selectedPiece}
          {selectedPiece} • rot {pose.rotation * 90}° • {pose.flipped ? 'flipped' : 'normal'}
        {:else}
          all pieces used
        {/if}
      </span>
      <span class="pose-readout">
        {#if isTouchDevice}
          tap: select piece, tap board: place/remove
        {:else}
          keys: piece letter to select, R/Shift+R rotate, X flip, Esc clear ghost
        {/if}
      </span>
      {#if selectedPiece && transformed}
        {@const dims = bounds(transformed)}
        <span
          class="active-preview"
          style={`--rows:${dims.rows};--cols:${dims.cols};--c:${PIECE_COLORS[selectedPiece]}`}
          aria-label="Active transformed preview"
        >
          {#each transformed as [r, c]}
            <span class="cell" style={`grid-row:${r + 1};grid-column:${c + 1}`}></span>
          {/each}
        </span>
      {/if}
    </div>

    <div class="board-wrap">
      <BoardWebGL
        placements={visiblePlacements}
        ghost={ghostPlacement && selectedPiece ? { name: selectedPiece, cells: ghostPlacement.cells, valid: ghostValid } : null}
        interactive={!isAnimating}
        on:cellhover={onBoardHover}
        on:cellclick={onBoardClick}
      />
    </div>

    <div class="slider-row">
      <label for="fixed">Already placed: {prefixCount}</label>
      <input
        id="fixed"
        type="range"
        min="0"
        max={placements.length}
        value={prefixCount}
        disabled={isAnimating}
        on:input={onSliderInput}
      />
      <span>{placements.length} total in snapshot</span>
    </div>

    <div class="slider-row">
      <label for="speed">Animate speed: {initialSpeedMultiplier.toFixed(2)}x</label>
      <input
        id="speed"
        type="range"
        min="0"
        max="100"
        step="1"
        value={speedSlider}
        disabled={isAnimating}
        on:input={onInitialSpeedInput}
      />
      <span>linear slider, exponential speed mapping</span>
    </div>
  </section>

  <aside class="pane solved-pane">
    <header>
      <h2>Solved</h2>
      <p>Click any solved rectangle to copy it into Solver.</p>
    </header>

    {#if solvedSolutions.length === 0}
      <div class="empty">No solved rectangles yet.</div>
    {:else}
      <div class="solved-list">
        {#each solvedSolutions as solution, idx}
          <button class="solved-card" on:click={() => importSolved(idx)} disabled={isAnimating}>
            <div class="solved-index">Rectangle {idx + 1}</div>
            <div class="mini-board">
              <BoardWebGL placements={solution} interactive={false} />
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </aside>
</main>
