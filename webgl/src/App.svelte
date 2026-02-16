<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import BoardWebGL from './lib/BoardWebGL.svelte';
  import {
    PIECE_COLORS,
    PIECE_ORDER,
    PIECES,
    cellsForPose,
    placeAtAnchor,
    solutionKey,
  } from './lib/pentomino';
  import type { Placement, PieceName, Pose } from './lib/pentomino';
  import {
    canApplyTriplicationPlacement,
    createTriplicationProblem,
    solveTriplicationFromPlacements,
    solveTriplicationWithTraceFromPlacements,
  } from './lib/triplication';
  import type { TriplicationProblem, TriplicationTraceEvent } from './lib/triplication';
  import {
    canApplyPlacement,
    countSolutionsFromPlacements,
    solveFromPlacements,
    solveWithTraceFromPlacements,
  } from './lib/solver';
  import type { TraceEvent } from './lib/solver';

  type Hover = { row: number; col: number } | null;
  type SavedSolution = { placements: Placement[]; rows: number; cols: number };
  type SavedTriplicationSolution = { placements: Placement[]; problem: TriplicationProblem };

  const isTouchDevice =
    typeof window !== 'undefined' &&
    ('ontouchstart' in window ||
      window.matchMedia?.('(pointer: coarse)').matches ||
      navigator.maxTouchPoints > 0);
  const repoUrl = 'https://github.com/cognominal/pentomanim';
  const boardSizeOptions = ['20x3', '15x4', '12x5', '10x6'] as const;
  const paneOptions = ['rectangle', 'triplication'] as const;

  let selectedPiece: PieceName | null = 'F';
  let selectedBoardSize: (typeof boardSizeOptions)[number] = '10x6';
  let activePane: (typeof paneOptions)[number] = 'rectangle';
  let pose: Pose = { rotation: 0, flipped: false };
  let hover: Hover = null;
  let placements: Placement[] = [];
  let prefixCount = 0;
  let solvedSolutions: SavedSolution[] = [];
  let status = isTouchDevice
    ? 'Pick a piece and tap the board to place it.'
    : 'Pick a piece and click the board to place it.';
  let currentPrefixSolutions: number | null = null;
  let isAnimating = false;
  let animationTimer: ReturnType<typeof setInterval> | null = null;
  let animationStepsUsed = 0;
  let animationTraceLength = 0;
  let animationStartSliderValue: number | null = null;
  let showRepoLink = false;
  let triplicationProblem: TriplicationProblem | null = null;
  let triplicationStatus = 'Press New Triplication Problem to generate a solvable puzzle.';
  let isGeneratingTriplication = false;
  let tripSelectedPiece: PieceName | null = null;
  let tripPose: Pose = { rotation: 0, flipped: false };
  let tripHover: Hover = null;
  let tripPlacements: Placement[] = [];
  let tripPrefixCount = 0;
  let tripSolvedSolutions: SavedTriplicationSolution[] = [];
  let tripIsAnimating = false;
  let tripAnimationTimer: ReturnType<typeof setInterval> | null = null;
  let tripAnimationStepsUsed = 0;
  let tripAnimationStartSliderValue: number | null = null;
  const MIN_INITIAL_SPEED = 0.01;
  const MAX_INITIAL_SPEED = 1000000;
  const SPEED_EXP_RANGE = Math.log2(MAX_INITIAL_SPEED / MIN_INITIAL_SPEED);
  const DEFAULT_INITIAL_SPEED = 1;
  const TRIP_DEFAULT_INITIAL_SPEED = 0.1;
  let speedSlider = (100 * Math.log2(DEFAULT_INITIAL_SPEED / MIN_INITIAL_SPEED)) / SPEED_EXP_RANGE;
  let tripSpeedSlider = (100 * Math.log2(TRIP_DEFAULT_INITIAL_SPEED / MIN_INITIAL_SPEED)) / SPEED_EXP_RANGE;
  $: initialSpeedMultiplier = speedFromSlider(speedSlider);
  $: tripInitialSpeedMultiplier = speedFromSlider(tripSpeedSlider);

  $: visiblePlacements = placements.slice(0, prefixCount);
  $: [boardCols, boardRows] = selectedBoardSize.split('x').map(Number) as [number, number];
  $: isLongRectangleBoard = boardCols / boardRows >= 5;
  $: rectangleBoardRotatedView = isLongRectangleBoard;
  $: rectangleDisplayRows = rectangleBoardRotatedView ? boardCols : boardRows;
  $: rectangleDisplayCols = rectangleBoardRotatedView ? boardRows : boardCols;
  $: isErrorStatus = status.toLowerCase().includes('no completion');
  $: showResetPrefixAction = currentPrefixSolutions === 0 && !isAnimating && visiblePlacements.length > 0;
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
    inBoundsForBoard(ghostPlacement.cells) &&
    canApplyPlacement(visiblePlacements, ghostPlacement as Placement, boardRows, boardCols);

  $: tripVisiblePlacements = tripPlacements.slice(0, tripPrefixCount);
  $: tripUsedNames = new Set(tripVisiblePlacements.map((p) => p.name));
  $: tripAvailablePieces = triplicationProblem
    ? triplicationProblem.selectedPieces.filter((name) => !tripUsedNames.has(name))
    : [];
  $: if (tripSelectedPiece && tripUsedNames.has(tripSelectedPiece)) {
    tripSelectedPiece = tripAvailablePieces[0] ?? null;
  }
  $: tripTransformed = tripSelectedPiece ? cellsForPose(tripSelectedPiece, tripPose) : null;
  $: tripGhostPlacement =
    triplicationProblem && tripSelectedPiece && tripTransformed && tripHover
      ? {
          name: tripSelectedPiece,
          cells: placeAtAnchor(tripTransformed, tripHover.row, tripHover.col),
        }
      : null;
  $: tripGhostValid =
    !!triplicationProblem &&
    !!tripGhostPlacement &&
    canApplyTriplicationPlacement(triplicationProblem, tripVisiblePlacements, tripGhostPlacement as Placement);

  function onBoardSizeChange(event: Event): void {
    const target = event.currentTarget as HTMLSelectElement;
    selectedBoardSize = target.value as (typeof boardSizeOptions)[number];
    placements = [];
    prefixCount = 0;
    hover = null;
    selectedPiece = 'F';
    solvedSolutions = [];
    currentPrefixSolutions = null;
    status = `Board size set to ${selectedBoardSize}. Board cleared.`;
  }

  function cloneTriplicationProblem(problem: TriplicationProblem): TriplicationProblem {
    return {
      triplicatedPiece: problem.triplicatedPiece,
      rows: problem.rows,
      cols: problem.cols,
      maskCells: problem.maskCells.map(([r, c]) => [r, c] as [number, number]),
      selectedPieces: [...problem.selectedPieces],
    };
  }

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
    const key = `${boardRows}x${boardCols}:${solutionKey(solution)}`;
    if (!solvedSolutions.some((s) => `${s.rows}x${s.cols}:${solutionKey(s.placements)}` === key)) {
      solvedSolutions = [{ placements: clonePlacements(solution), rows: boardRows, cols: boardCols }, ...solvedSolutions];
    }
  }

  function inBoundsForBoard(cells: [number, number][]): boolean {
    return cells.every(([r, c]) => r >= 0 && r < boardRows && c >= 0 && c < boardCols);
  }

  function toDisplayCell(row: number, col: number, rows: number, rotated: boolean): [number, number] {
    if (!rotated) {
      return [row, col];
    }
    return [col, rows - 1 - row];
  }

  function fromDisplayCell(row: number, col: number, rows: number, rotated: boolean): [number, number] {
    if (!rotated) {
      return [row, col];
    }
    return [rows - 1 - col, row];
  }

  function toDisplayPlacements(data: Placement[], rows: number, rotated: boolean): Placement[] {
    if (!rotated) {
      return data;
    }
    return data.map((p) => ({
      name: p.name,
      cells: p.cells.map(([r, c]) => toDisplayCell(r, c, rows, true) as [number, number]),
    }));
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
    currentPrefixSolutions = null;
  }

  function commitPlacement(candidate: Placement): void {
    if (isAnimating) {
      return;
    }
    if (!inBoundsForBoard(candidate.cells) || !canApplyPlacement(visiblePlacements, candidate, boardRows, boardCols)) {
      return;
    }
    truncateToPrefix();
    placements = [...placements, clonePlacements([candidate])[0]];
    prefixCount = placements.length;

    if (placements.length === PIECE_ORDER.length) {
      addSolved(placements);
      clearSolverAfterSolved('Rectangle solved manually. Added to Solved; Solver cleared.');
      return;
    }

    const solutionStats = countSolutionsFromPlacements(clonePlacements(placements), 200, boardRows, boardCols);
    currentPrefixSolutions = solutionStats.count;
    const noun = solutionStats.count === 1 ? 'solution' : 'solutions';
    status = `${candidate.name} placed. ${solutionStats.count} ${noun} for this prefix${solutionStats.complete ? '' : ' and counting'}.`;
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
    currentPrefixSolutions = null;
    status = `${hit.name} removed and selected.`;
    return true;
  }

  function onBoardClick(event: CustomEvent<{ row: number; col: number }>): void {
    if (isAnimating) {
      return;
    }
    const [row, col] = fromDisplayCell(
      event.detail.row,
      event.detail.col,
      boardRows,
      rectangleBoardRotatedView,
    );
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
    const solved = solveFromPlacements(start, boardRows, boardCols);
    if (!solved) {
      currentPrefixSolutions = 0;
      status = 'No completion found from the current prefix.';
      return;
    }
    currentPrefixSolutions = null;
    const snapshot = clonePlacements(solved);
    addSolved(snapshot);
    clearSolverAfterSolved('Solved from current state. Added to Solved; Solver cleared.');
  }

  function importSolved(index: number): void {
    if (isAnimating) {
      return;
    }
    const chosen = solvedSolutions[index];
    selectedBoardSize = `${chosen.cols}x${chosen.rows}` as (typeof boardSizeOptions)[number];
    placements = clonePlacements(chosen.placements);
    prefixCount = chosen.placements.length;
    selectedPiece = null;
    currentPrefixSolutions = null;
    status = `Loaded solved rectangle #${index + 1} into Solver.`;
  }

  function addTripSolved(problem: TriplicationProblem, solution: Placement[]): void {
    if (solution.length !== problem.selectedPieces.length) {
      return;
    }
    const key = `${problem.triplicatedPiece}:${problem.rows}x${problem.cols}:${problem.selectedPieces.join('')}:${solutionKey(solution)}`;
    if (
      tripSolvedSolutions.some(
        (saved) =>
          `${saved.problem.triplicatedPiece}:${saved.problem.rows}x${saved.problem.cols}:${saved.problem.selectedPieces.join('')}:${solutionKey(saved.placements)}` ===
          key,
      )
    ) {
      return;
    }
    tripSolvedSolutions = [
      { problem: cloneTriplicationProblem(problem), placements: clonePlacements(solution) },
      ...tripSolvedSolutions,
    ];
  }

  function clearTripSolverAfterSolved(message: string): void {
    if (!triplicationProblem) {
      return;
    }
    tripPlacements = [];
    tripPrefixCount = 0;
    tripHover = null;
    tripSelectedPiece = triplicationProblem.selectedPieces[0] ?? null;
    tripResetPose();
    triplicationStatus = message;
  }

  function importTripSolved(index: number): void {
    if (tripIsAnimating) {
      return;
    }
    const chosen = tripSolvedSolutions[index];
    triplicationProblem = cloneTriplicationProblem(chosen.problem);
    tripPlacements = clonePlacements(chosen.placements);
    tripPrefixCount = tripPlacements.length;
    tripSelectedPiece = null;
    tripHover = null;
    tripResetPose();
    triplicationStatus = `Loaded solved triplication #${index + 1} into Triplication Solver.`;
  }

  function onKey(event: KeyboardEvent): void {
    if (activePane === 'triplication') {
      if (!triplicationProblem || tripIsAnimating) {
        return;
      }
      const keyUpper = event.key.toUpperCase();
      if (PIECE_ORDER.includes(keyUpper as PieceName)) {
        const piece = keyUpper as PieceName;
        if (tripAvailablePieces.includes(piece)) {
          selectTripPiece(piece);
        }
        return;
      }
      if (!tripSelectedPiece) {
        return;
      }
      if (event.key === 'r' && event.shiftKey) {
        tripRotateLeft();
        return;
      }
      if (event.key.toLowerCase() === 'r') {
        tripRotateRight();
        return;
      }
      if (event.key.toLowerCase() === 'x') {
        tripFlip();
        return;
      }
      if (event.key === 'Escape') {
        tripHover = null;
      }
      return;
    }

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

  function newTriplicationProblem(): void {
    isGeneratingTriplication = true;
    triplicationStatus = 'Generating solvable triplication puzzle...';
    setTimeout(() => {
      const problem = createTriplicationProblem(400, 400000);
      if (!problem) {
        triplicationStatus = 'No solvable problem found in this batch. Try again.';
        isGeneratingTriplication = false;
        return;
      }
      triplicationProblem = problem;
      tripSelectedPiece = problem.selectedPieces[0] ?? null;
      tripPose = { rotation: 0, flipped: false };
      tripHover = null;
      tripPlacements = [];
      tripPrefixCount = 0;
      tripAnimationStepsUsed = 0;
      stopTripAnimationTimer();
      tripIsAnimating = false;
      triplicationStatus = `Triplicated ${problem.triplicatedPiece} selected with 9 pieces.`;
      isGeneratingTriplication = false;
    }, 0);
  }

  function onBoardHover(event: CustomEvent<{ row: number; col: number } | null>): void {
    if (isAnimating) {
      return;
    }
    if (!event.detail) {
      hover = null;
      return;
    }
    const [row, col] = fromDisplayCell(
      event.detail.row,
      event.detail.col,
      boardRows,
      rectangleBoardRotatedView,
    );
    hover = { row, col };
  }

  function sliderChanged(value: number): void {
    prefixCount = Math.max(0, Math.min(value, placements.length));
    currentPrefixSolutions = null;
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

  function onTripInitialSpeedInput(event: Event): void {
    if (tripIsAnimating) {
      return;
    }
    const target = event.currentTarget as HTMLInputElement;
    tripSpeedSlider = Number(target.value);
  }

  function speedFromSlider(value: number): number {
    return MIN_INITIAL_SPEED * 2 ** ((value / 100) * SPEED_EXP_RANGE);
  }

  function sliderFromSpeed(speed: number): number {
    const clamped = Math.max(MIN_INITIAL_SPEED, Math.min(speed, MAX_INITIAL_SPEED));
    return (100 * Math.log2(clamped / MIN_INITIAL_SPEED)) / SPEED_EXP_RANGE;
  }

  function formatSpeed(speed: number): string {
    return speed.toLocaleString('en-US', { useGrouping: false, minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }

  function applyTraceEvent(snapshot: Placement[], event: TraceEvent): Placement[] {
    if (event.type === 'place') {
      return [...snapshot, clonePlacements([event.placement])[0]];
    }
    return snapshot.filter((p) => p.name !== event.placement.name);
  }

  function longestValidPrefix(source: Placement[]): Placement[] {
    for (let len = source.length; len >= 0; len -= 1) {
      const candidate = clonePlacements(source.slice(0, len));
      if (solveFromPlacements(candidate, boardRows, boardCols) !== null) {
        return candidate;
      }
    }
    return [];
  }

  function resetToLongestValidPrefix(): void {
    const longest = longestValidPrefix(clonePlacements(visiblePlacements));
    placements = clonePlacements(longest);
    prefixCount = longest.length;
    currentPrefixSolutions = null;
    status = `Reset to longest valid prefix (${longest.length} pieces).`;
  }

  function stopAnimationTimer(): void {
    if (animationTimer) {
      clearInterval(animationTimer);
      animationTimer = null;
    }
  }

  function stopTripAnimationTimer(): void {
    if (tripAnimationTimer) {
      clearInterval(tripAnimationTimer);
      tripAnimationTimer = null;
    }
  }

  function tripRotateLeft(): void {
    tripPose = { ...tripPose, rotation: ((tripPose.rotation + 3) % 4) as Pose['rotation'] };
  }

  function tripRotateRight(): void {
    tripPose = { ...tripPose, rotation: ((tripPose.rotation + 1) % 4) as Pose['rotation'] };
  }

  function tripFlip(): void {
    tripPose = { ...tripPose, flipped: !tripPose.flipped };
  }

  function tripResetPose(): void {
    tripPose = { rotation: 0, flipped: false };
  }

  function selectTripPiece(name: PieceName): void {
    if (tripIsAnimating) {
      return;
    }
    tripSelectedPiece = name;
    tripResetPose();
  }

  function commitTripPlacement(candidate: Placement): void {
    if (!triplicationProblem || tripIsAnimating) {
      return;
    }
    if (!canApplyTriplicationPlacement(triplicationProblem, tripVisiblePlacements, candidate)) {
      return;
    }
    if (tripPrefixCount < tripPlacements.length) {
      tripPlacements = tripPlacements.slice(0, tripPrefixCount);
    }
    tripPlacements = [...tripPlacements, clonePlacements([candidate])[0]];
    tripPrefixCount = tripPlacements.length;
    if (tripPlacements.length === triplicationProblem.selectedPieces.length) {
      addTripSolved(triplicationProblem, tripPlacements);
      clearTripSolverAfterSolved('Triplication solved manually. Added to Solved; Solver cleared.');
      return;
    }
    triplicationStatus = `${candidate.name} placed on triplication board.`;
  }

  function removeTripPieceAt(row: number, col: number): boolean {
    const hit = tripVisiblePlacements.find((p) => p.cells.some(([r, c]) => r === row && c === col));
    if (!hit) {
      return false;
    }
    tripPlacements = tripVisiblePlacements.filter((p) => p.name !== hit.name);
    tripPrefixCount = tripPlacements.length;
    tripSelectedPiece = hit.name;
    tripResetPose();
    tripHover = null;
    triplicationStatus = `${hit.name} removed and selected.`;
    return true;
  }

  function onTripBoardHover(event: CustomEvent<{ row: number; col: number } | null>): void {
    if (tripIsAnimating) {
      return;
    }
    tripHover = event.detail;
  }

  function onTripBoardClick(event: CustomEvent<{ row: number; col: number }>): void {
    if (tripIsAnimating || !triplicationProblem) {
      return;
    }
    const { row, col } = event.detail;
    tripHover = { row, col };
    if (removeTripPieceAt(row, col)) {
      return;
    }
    if (!tripSelectedPiece || !tripTransformed) {
      return;
    }
    commitTripPlacement({ name: tripSelectedPiece, cells: placeAtAnchor(tripTransformed, row, col) });
  }

  function solveTriplicationNow(): void {
    if (!triplicationProblem || tripIsAnimating) {
      return;
    }
    const solved = solveTriplicationFromPlacements(triplicationProblem, clonePlacements(tripVisiblePlacements), 400000);
    if (!solved) {
      triplicationStatus = 'No completion found from the current triplication prefix.';
      return;
    }
    addTripSolved(triplicationProblem, solved);
    clearTripSolverAfterSolved('Triplication solved from current state. Added to Solved; Solver cleared.');
  }

  function animateTriplicationSolve(): void {
    if (!triplicationProblem) {
      return;
    }
    if (tripIsAnimating) {
      stopTripAnimationTimer();
      tripIsAnimating = false;
      if (tripAnimationStartSliderValue !== null) {
        tripSpeedSlider = tripAnimationStartSliderValue;
      }
      tripAnimationStartSliderValue = null;
      triplicationStatus = `Triplication animation paused at ${tripAnimationStepsUsed} steps.`;
      return;
    }
    const traced = solveTriplicationWithTraceFromPlacements(
      triplicationProblem,
      clonePlacements(tripVisiblePlacements),
      400000,
    );
    if (!traced) {
      triplicationStatus = 'No completion found from the current triplication prefix.';
      return;
    }
    const { solution, trace } = traced;
    if (trace.length === 0) {
      tripPlacements = clonePlacements(solution);
      tripPrefixCount = tripPlacements.length;
      triplicationStatus = 'Triplication puzzle already solved.';
      return;
    }

    tripIsAnimating = true;
    tripSelectedPiece = null;
    tripHover = null;
    tripAnimationStepsUsed = 0;
    let cursor = 0;
    let working = clonePlacements(tripVisiblePlacements);
    const startedAt = Date.now();
    let stepBudget = 0;
    const baseInitialSpeed = tripInitialSpeedMultiplier;
    tripAnimationStartSliderValue = tripSpeedSlider;

    stopTripAnimationTimer();
    tripAnimationTimer = setInterval(() => {
      const elapsedMs = Date.now() - startedAt;
      const speedFactor = baseInitialSpeed * 2 ** (elapsedMs / 5000);
      tripSpeedSlider = sliderFromSpeed(speedFactor);
      stepBudget += speedFactor;
      const stepsThisTick = Math.max(1, Math.floor(stepBudget));
      stepBudget -= stepsThisTick;
      for (let i = 0; i < stepsThisTick && cursor < trace.length; i += 1) {
        const step = trace[cursor];
        if (step.type === 'place') {
          working = [...working, clonePlacements([step.placement])[0]];
        } else {
          working = working.filter((p) => p.name !== step.placement.name);
        }
        cursor += 1;
      }
      tripPlacements = clonePlacements(working);
      tripPrefixCount = tripPlacements.length;
      tripAnimationStepsUsed = cursor;
      triplicationStatus = `Animating triplication solve: ${cursor}/${trace.length} steps`;

      if (cursor >= trace.length) {
        stopTripAnimationTimer();
        tripIsAnimating = false;
        if (tripAnimationStartSliderValue !== null) {
          tripSpeedSlider = tripAnimationStartSliderValue;
        }
        tripAnimationStartSliderValue = null;
        addTripSolved(triplicationProblem, solution);
        clearTripSolverAfterSolved('Triplication animation complete. Added to Solved; Solver cleared.');
      }
    }, 100);
  }

  function onTripSliderInput(event: Event): void {
    if (tripIsAnimating) {
      return;
    }
    const target = event.currentTarget as HTMLInputElement;
    tripPrefixCount = Math.max(0, Math.min(Number(target.value), tripPlacements.length));
    triplicationStatus = `${tripPrefixCount} pentominoes fixed in Triplication Solver.`;
  }

  function stopAnimationAtCurrentStage(): void {
    stopAnimationTimer();
    isAnimating = false;
    if (animationStartSliderValue !== null) {
      speedSlider = animationStartSliderValue;
    }
    status = `Animation paused at step ${animationStepsUsed}/${animationTraceLength}.`;
    animationStartSliderValue = null;
  }

  function animateSolve(): void {
    if (isAnimating) {
      stopAnimationAtCurrentStage();
      return;
    }

    const rawStart = clonePlacements(visiblePlacements);
    const start = longestValidPrefix(rawStart);
    if (start.length !== rawStart.length) {
      placements = clonePlacements(start);
      prefixCount = start.length;
      status = `Restarted from longest valid prefix (${start.length} pieces).`;
    }

    animationStepsUsed = 0;
    const traced = solveWithTraceFromPlacements(start, 200000, boardRows, boardCols);
    let solution: Placement[];
    let trace: TraceEvent[];

    if (!traced) {
      const solved = solveFromPlacements(start, boardRows, boardCols);
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
    animationTraceLength = trace.length;
    status = `Animating solve: 0/${trace.length} steps`;

    let cursor = 0;
    let working = clonePlacements(start);
    const startedAt = Date.now();
    const baseInitialSpeed = initialSpeedMultiplier;
    animationStartSliderValue = speedSlider;
    let stepBudget = 0;

    stopAnimationTimer();
    animationTimer = setInterval(() => {
      const elapsedMs = Date.now() - startedAt;
      const speedFactor = baseInitialSpeed * 2 ** (elapsedMs / 5000);
      speedSlider = sliderFromSpeed(speedFactor);
      stepBudget += speedFactor;
      const stepsThisTick = Math.floor(stepBudget);
      if (stepsThisTick <= 0) {
        status = `Animating solve: ${cursor}/${trace.length} steps (${formatSpeed(speedFactor)}x speed)`;
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
      status = `Animating solve: ${cursor}/${trace.length} steps (${formatSpeed(speedFactor)}x speed)`;

      if (cursor >= trace.length) {
        stopAnimationTimer();
        isAnimating = false;
        if (animationStartSliderValue !== null) {
          speedSlider = animationStartSliderValue;
        }
        animationStartSliderValue = null;
        addSolved(solution);
        clearSolverAfterSolved('Animated solve complete. Added to Solved; Solver cleared.');
      }
    }, 100);
  }

  onDestroy(() => {
    stopAnimationTimer();
    stopTripAnimationTimer();
  });

  onMount(() => {
    newTriplicationProblem();
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

<main class:touch-mode={isTouchDevice} class:long-rect-mode={activePane === 'rectangle' && isLongRectangleBoard}>
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

  <nav class="pane pane-tabs">
    <button
      class="tab-btn"
      class:active={activePane === 'rectangle'}
      on:click={() => (activePane = 'rectangle')}
    >
      Rectangle Solver
    </button>
    <button
      class="tab-btn"
      class:active={activePane === 'triplication'}
      on:click={() => (activePane = 'triplication')}
    >
      Triplication Solver
    </button>
  </nav>

  {#if activePane === 'rectangle'}
  <section class="pane solver-pane">
    <header>
      <div class="solver-title-row">
        <h2>Rectangle Solver</h2>
        <label class="board-size-select">
          <span>Size</span>
          <select value={selectedBoardSize} on:change={onBoardSizeChange}>
            {#each boardSizeOptions as size}
              <option value={size}>{size}</option>
            {/each}
          </select>
        </label>
      </div>
      <div class="status-row">
        <p class:error-status={isErrorStatus}>{status}</p>
        {#if showResetPrefixAction}
          <button class="status-action" on:click={resetToLongestValidPrefix}>
            Reset to the longest valid prefix
          </button>
        {/if}
      </div>
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
          {#if !isTouchDevice}
            <span class="label">{name}</span>
          {/if}
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
      <button class="solve" on:click={animateSolve}>{isAnimating ? 'Stop Animation' : 'Animate Solve'}</button>
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

    <div class="board-wrap" style={`--board-ratio:${rectangleDisplayCols / rectangleDisplayRows}`}>
      <BoardWebGL
        rows={rectangleDisplayRows}
        cols={rectangleDisplayCols}
        placements={toDisplayPlacements(visiblePlacements, boardRows, rectangleBoardRotatedView)}
        ghost={ghostPlacement && selectedPiece
          ? {
              name: selectedPiece,
              cells: ghostPlacement.cells.map(([r, c]) => toDisplayCell(r, c, boardRows, rectangleBoardRotatedView)),
              valid: ghostValid,
            }
          : null}
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
        <label for="speed">Animate speed: {formatSpeed(initialSpeedMultiplier)}x</label>
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
      <p>{isTouchDevice ? 'Tap any solved rectangle to copy it into Solver.' : 'Click any solved rectangle to copy it into Solver.'}</p>
    </header>

    {#if solvedSolutions.length === 0}
      <div class="empty">No solved rectangles yet.</div>
    {:else}
      <div class="solved-list">
        {#each solvedSolutions as solution, idx}
          {@const rotatedSolutionView = solution.cols / solution.rows >= 5}
          <button class="solved-card" on:click={() => importSolved(idx)} disabled={isAnimating}>
            <div class="solved-index">Rectangle {idx + 1}</div>
            <div
              class="mini-board"
              style={`--board-ratio:${(rotatedSolutionView ? solution.rows : solution.cols) / (rotatedSolutionView ? solution.cols : solution.rows)}`}
            >
              <BoardWebGL
                placements={toDisplayPlacements(solution.placements, solution.rows, rotatedSolutionView)}
                rows={rotatedSolutionView ? solution.cols : solution.rows}
                cols={rotatedSolutionView ? solution.rows : solution.cols}
                interactive={false}
              />
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </aside>
  {:else}
  <section class="pane triplication-solver-pane">
    <header>
      <div class="solver-title-row">
        <h2>Triplication Solver</h2>
        <button class="solve" on:click={newTriplicationProblem} disabled={isGeneratingTriplication}>
          New Triplication Problem
        </button>
      </div>
      <p class:error-status={triplicationStatus.toLowerCase().includes('no completion')}>{triplicationStatus}</p>
    </header>

    {#if triplicationProblem}
      <div class="piece-bank">
        {#each triplicationProblem.selectedPieces as name}
          {@const disabled = tripUsedNames.has(name)}
          {@const shape = pieceCells(name)}
          {@const dims = bounds(shape)}
          <button
            class="piece-btn"
            class:selected={tripSelectedPiece === name}
            class:used={disabled}
            on:click={() => selectTripPiece(name)}
            disabled={disabled || tripIsAnimating}
            aria-label={`Select ${name}`}
          >
            {#if !isTouchDevice}
              <span class="label">{name}</span>
            {/if}
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
        <button on:click={tripRotateLeft} disabled={!tripSelectedPiece}>Rotate ⟲</button>
        <button on:click={tripRotateRight} disabled={!tripSelectedPiece}>Rotate ⟳</button>
        <button on:click={tripFlip} disabled={!tripSelectedPiece}>Flip ↔</button>
        <button on:click={tripResetPose} disabled={!tripSelectedPiece}>Reset</button>
        <button class="solve" on:click={solveTriplicationNow} disabled={tripIsAnimating}>Solve</button>
        <button class="solve" on:click={animateTriplicationSolve}>
          {tripIsAnimating ? 'Stop Animation' : 'Animate Solve'}
        </button>
        <span class="pose-readout">steps used: {tripAnimationStepsUsed}</span>
        <span class="pose-readout">
          {#if tripSelectedPiece}
            {tripSelectedPiece} • rot {tripPose.rotation * 90}° • {tripPose.flipped ? 'flipped' : 'normal'}
          {:else}
            all selected pieces used
          {/if}
        </span>
        <span class="pose-readout">
          {#if isTouchDevice}
            tap: select piece, tap board: place/remove
          {:else}
            keys: piece letter to select, R/Shift+R rotate, X flip, Esc clear ghost
          {/if}
        </span>
        {#if tripSelectedPiece && tripTransformed}
          {@const dims = bounds(tripTransformed)}
          <span
            class="active-preview"
            style={`--rows:${dims.rows};--cols:${dims.cols};--c:${PIECE_COLORS[tripSelectedPiece]}`}
            aria-label="Active transformed preview"
          >
            {#each tripTransformed as [r, c]}
              <span class="cell" style={`grid-row:${r + 1};grid-column:${c + 1}`}></span>
            {/each}
          </span>
        {/if}
      </div>

      <div class="board-wrap" style={`--board-ratio:${triplicationProblem.cols / triplicationProblem.rows}`}>
        <BoardWebGL
          rows={triplicationProblem.rows}
          cols={triplicationProblem.cols}
          placements={tripVisiblePlacements}
          maskCells={triplicationProblem.maskCells}
          ghost={tripGhostPlacement && tripSelectedPiece ? { name: tripSelectedPiece, cells: tripGhostPlacement.cells, valid: tripGhostValid } : null}
          interactive={!tripIsAnimating}
          on:cellhover={onTripBoardHover}
          on:cellclick={onTripBoardClick}
        />
      </div>

      <div class="slider-row">
        <label for="trip-fixed">Already placed: {tripPrefixCount}</label>
        <input
          id="trip-fixed"
          type="range"
          min="0"
          max={tripPlacements.length}
          value={tripPrefixCount}
          disabled={tripIsAnimating}
          on:input={onTripSliderInput}
        />
        <span>{tripPlacements.length} total in snapshot</span>
      </div>

      <div class="slider-row">
        <label for="trip-speed">Animate speed: {formatSpeed(tripInitialSpeedMultiplier)}x</label>
        <input
          id="trip-speed"
          type="range"
          min="0"
          max="100"
          step="1"
          value={tripSpeedSlider}
          disabled={tripIsAnimating}
          on:input={onTripInitialSpeedInput}
        />
        <span>linear slider, exponential speed mapping</span>
      </div>
    {/if}
  </section>

  <aside class="pane solved-pane trip-solved-pane">
    <header>
      <h2>Solved</h2>
      <p>
        {isTouchDevice
          ? 'Tap any solved triplication to copy it into Triplication Solver.'
          : 'Click any solved triplication to copy it into Triplication Solver.'}
      </p>
    </header>

    {#if tripSolvedSolutions.length === 0}
      <div class="empty">No solved triplication boards yet.</div>
    {:else}
      <div class="solved-list">
        {#each tripSolvedSolutions as solution, idx}
          <button class="solved-card" on:click={() => importTripSolved(idx)} disabled={tripIsAnimating}>
            <div class="solved-index">Triplication {idx + 1}</div>
            <div class="mini-board" style={`--board-ratio:${solution.problem.cols / solution.problem.rows}`}>
              <BoardWebGL
                placements={solution.placements}
                maskCells={solution.problem.maskCells}
                rows={solution.problem.rows}
                cols={solution.problem.cols}
                interactive={false}
              />
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </aside>
  {/if}
</main>
