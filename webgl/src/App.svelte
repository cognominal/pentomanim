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
    solveFromPlacements,
    solveWithTraceFromPlacements,
  } from './lib/solver';
  import type { TraceEvent } from './lib/solver';

  type Hover = { row: number; col: number } | null;
  type SavedSolution = { placements: Placement[]; rows: number; cols: number };
  type SavedTriplicationSolution = { placements: Placement[]; problem: TriplicationProblem };
  type SolverCountResponse = { requestId: number; count: number; complete: boolean };
  type ViewportPoint = { x: number; y: number };
  type StatusFlight = {
    id: number;
    text: string;
    x: number;
    y: number;
    dx: number;
    dy: number;
    active: boolean;
  };
  type PickerDragState = {
    pointerId: number;
    pointerType: string;
    piece: PieceName;
  };

  const isTouchDevice =
    typeof window !== 'undefined' &&
    ('ontouchstart' in window ||
      window.matchMedia?.('(pointer: coarse)').matches ||
      navigator.maxTouchPoints > 0);
  const COMPACT_LAYOUT_MAX_WIDTH = 980;
  const repoUrl = 'https://github.com/cognominal/pentomanim';
  const boardSizeOptions = ['20x3', '15x4', '12x5', '10x6'] as const;
  const paneOptions = ['rectangle', 'triplication'] as const;
  const touchViewOptions = ['solver', 'solved'] as const;
  const SOLVED_TRANSITION_MS = 2000;
  const STATUS_FLIGHT_MS = 1000;

  let selectedPiece: PieceName | null = 'F';
  let selectedBoardSize: (typeof boardSizeOptions)[number] = '10x6';
  let activePane: (typeof paneOptions)[number] = 'rectangle';
  let touchViewMode: (typeof touchViewOptions)[number] = 'solver';
  let pose: Pose = { rotation: 0, flipped: false };
  let hover: Hover = null;
  let placements: Placement[] = [];
  let prefixCount = 0;
  let solvedSolutions: SavedSolution[] = [];
  let useTouchLayout =
    isTouchDevice ||
    (typeof window !== 'undefined' && window.innerWidth <= COMPACT_LAYOUT_MAX_WIDTH);
  let status = useTouchLayout
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
  let rectangleBoardWrapEl: HTMLDivElement | null = null;
  let tripBoardWrapEl: HTMLDivElement | null = null;
  let rectangleStatusEl: HTMLParagraphElement | null = null;
  let tripStatusEl: HTMLParagraphElement | null = null;
  let solvedToggleEl: HTMLButtonElement | null = null;
  let paneTabsEl: HTMLElement | null = null;
  let rectangleSolvedTransitionTimer: ReturnType<typeof setTimeout> | null = null;
  let tripSolvedTransitionTimer: ReturnType<typeof setTimeout> | null = null;
  let rectangleSolvedTransitioning = false;
  let tripSolvedTransitioning = false;
  let rectangleSolvedTransitionStyle = '';
  let tripSolvedTransitionStyle = '';
  let solverCountWorker: Worker | null = null;
  let solverCountRequestSeq = 0;
  let activeSolverCountRequestId = -1;
  let rectangleDragActive = false;
  let rectangleDragPointerType: string | null = null;
  let rectanglePickerDrag: PickerDragState | null = null;
  let tripDragActive = false;
  let rectangleDraggedPlacement: Placement | null = null;
  let tripDraggedPlacement: Placement | null = null;
  let rectangleSnapTimer: ReturnType<typeof setTimeout> | null = null;
  let rectangleSnapRaf = 0;
  let rectangleSnapAnimating = false;
  let rectangleDragMoved = false;
  let rectangleDraggedOriginKey: string | null = null;
  let rectangleDraggedOriginPlacement: Placement | null = null;
  let rectangleDraggedPlacementValid = false;
  let rectangleFloatingPlacement: { name: PieceName; cells: [number, number][] } | null = null;
  let rectanglePointerPos: { row: number; col: number } | null = null;
  let rectangleDragStartPointer: { row: number; col: number } | null = null;
  let rectangleDragStartCells: [number, number][] | null = null;
  let rectangleHoverPointerPos: { row: number; col: number } | null = null;
  let rectanglePointerOverBoard = false;
  let rectangleGhostSnapOutline: [number, number][] = [];
  let rectangleGhostSnapRaf = 0;
  let rectangleGhostSnapTargetKey = '';
  let rectangleGhostSnapAnimSeq = 0;
  let showGhostSnapOutline = false;
  let rectangleTouchOverlayStyle = '';
  let rectangleTouchOverlayEl: HTMLDivElement | null = null;
  let rectanglePickerPointerClient: { x: number; y: number } | null = null;
  let statusFlight: StatusFlight | null = null;
  let statusFlightSeq = 0;
  let statusFlightTimer: ReturnType<typeof setTimeout> | null = null;
  let rectangleStatusDelayTimer: ReturnType<typeof setTimeout> | null = null;
  let tripStatusDelayTimer: ReturnType<typeof setTimeout> | null = null;
  const MIN_INITIAL_SPEED = 0.01;
  const MAX_INITIAL_SPEED = 1000000;
  const SPEED_EXP_RANGE = Math.log2(MAX_INITIAL_SPEED / MIN_INITIAL_SPEED);
  const DEFAULT_INITIAL_SPEED = 1;
  const TRIP_DEFAULT_INITIAL_SPEED = 0.1;
  let speedSlider = (100 * Math.log2(DEFAULT_INITIAL_SPEED / MIN_INITIAL_SPEED)) / SPEED_EXP_RANGE;
  let tripSpeedSlider = (100 * Math.log2(TRIP_DEFAULT_INITIAL_SPEED / MIN_INITIAL_SPEED)) / SPEED_EXP_RANGE;
  $: initialSpeedMultiplier = speedFromSlider(speedSlider);
  $: tripInitialSpeedMultiplier = speedFromSlider(tripSpeedSlider);
  $: rectangleSolvedCount = solvedSolutions.length;
  $: triplicationSolvedCount = tripSolvedSolutions.length;
  $: activeSolvedCount = activePane === 'rectangle' ? rectangleSolvedCount : triplicationSolvedCount;
  $: isRectangleLocked = isAnimating || rectangleSolvedTransitioning || rectangleSnapAnimating;
  $: isTriplicationLocked = tripIsAnimating || tripSolvedTransitioning;

  $: visiblePlacements = placements.slice(0, prefixCount);
  $: rectangleRenderPlacements = rectangleDragOriginName
    ? rectangleBasePlacements
    : visiblePlacements;
  $: rectangleDragOriginName = rectangleDraggedOriginPlacement?.name ?? null;
  $: rectangleDragInFlight =
    rectangleDragActive || rectanglePickerDrag !== null;
  $: rectanglePickerDragActive = rectanglePickerDrag !== null;
  $: rectangleBasePlacements = rectangleDragOriginName
    ? visiblePlacements.filter((p) => p.name !== rectangleDragOriginName)
    : visiblePlacements;
  $: rectangleSettleOutline = (() => {
    if (rectanglePickerDragActive) {
      return [];
    }
    if (rectangleDraggedOriginPlacement || rectangleDragInFlight) {
      if (rectangleDraggedPlacement !== null && rectangleDraggedPlacementValid) {
        return rectangleDraggedPlacement.cells.map(([r, c]) =>
          toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
        );
      }
      return [];
    }
    if (!showGhostSnapOutline) {
      return [];
    }
    return rectangleGhostSnapOutline.map(([r, c]) =>
      toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
    );
  })();
  $: [boardCols, boardRows] = selectedBoardSize.split('x').map(Number) as [number, number];
  $: isLongRectangleBoard = boardCols / boardRows >= 5;
  $: rectangleBoardRotatedView = isLongRectangleBoard;
  $: rectangleDisplayRows = rectangleBoardRotatedView ? boardCols : boardRows;
  $: rectangleDisplayCols = rectangleBoardRotatedView ? boardRows : boardCols;
  $: isErrorStatus =
    status.toLowerCase().includes('no completion') ||
    status.toLowerCase().includes('cannot place');
  $: isTripErrorStatus =
    triplicationStatus.toLowerCase().includes('no completion') ||
    triplicationStatus.toLowerCase().includes('cannot place');
  $: showResetPrefixAction = currentPrefixSolutions === 0 && !isAnimating && visiblePlacements.length > 0;
  $: usedNames = new Set(rectangleBasePlacements.map((p) => p.name));
  $: availablePieces = PIECE_ORDER.filter((name) => !usedNames.has(name));
  $: if (selectedPiece && usedNames.has(selectedPiece)) {
    selectedPiece = availablePieces[0] ?? null;
  }

  $: transformed = selectedPiece ? cellsForPose(selectedPiece, pose) : null;
  $: ghostPlacement =
    selectedPiece &&
    transformed &&
    rectangleHoverPointerPos &&
    !rectangleDragInFlight &&
    !rectangleDraggedPlacement &&
    !rectangleSnapAnimating &&
    !rectangleDraggedOriginPlacement
      ? {
          name: selectedPiece,
          cells: floatCellsAtPointerBarycenter(
            transformed,
            rectangleHoverPointerPos.row,
            rectangleHoverPointerPos.col,
          ),
        }
      : null;

  $: ghostValid =
    selectedPiece !== null &&
    transformed !== null &&
    rectangleHoverPointerPos !== null &&
    (() => {
      const snapped = snappedPlacementAtPointerBarycenter(
        selectedPiece,
        transformed,
        rectangleHoverPointerPos.row,
        rectangleHoverPointerPos.col,
      );
      return (
        inBoundsForBoard(snapped.cells) &&
        canApplyPlacement(rectangleBasePlacements, snapped, boardRows, boardCols)
      );
    })();

  $: ghostSnappedPlacement =
    selectedPiece !== null &&
    transformed !== null &&
    rectangleHoverPointerPos !== null &&
    !rectangleDragInFlight &&
    !rectangleDraggedPlacement &&
    !rectangleSnapAnimating &&
    !rectangleDraggedOriginPlacement
      ? snappedPlacementAtPointerBarycenter(
          selectedPiece,
          transformed,
          rectangleHoverPointerPos.row,
          rectangleHoverPointerPos.col,
        )
      : null;

  $: ghostOverlapsPlacement =
    ghostSnappedPlacement !== null &&
    hasPlacementOverlap(ghostSnappedPlacement.cells, rectangleBasePlacements);

  $: showGhostSnapOutline =
    ghostSnappedPlacement !== null &&
    ghostValid &&
    !ghostOverlapsPlacement &&
    !rectangleDragInFlight &&
    !rectangleDraggedOriginPlacement;

  $: rectangleTouchOverlayActive =
    useTouchLayout &&
    activePane === 'rectangle' &&
    touchViewMode === 'solver' &&
    rectangleDragInFlight &&
    (rectangleDragPointerType === 'touch' ||
      rectanglePickerDrag?.pointerType === 'touch');

  $: {
    rectangleTouchOverlayActive;
    rectangleDisplayRows;
    rectangleDisplayCols;
    rectangleBoardRotatedView;
    updateRectangleTouchOverlayStyle();
  }

  $: {
    if (rectanglePickerDrag && rectanglePickerPointerClient) {
      applyRectanglePickerDragPointer(
        rectanglePickerPointerClient.x,
        rectanglePickerPointerClient.y,
        true,
      );
    }
  }

  $: {
    setRectangleGhostSnapTarget(showGhostSnapOutline ? ghostSnappedPlacement.cells : []);
  }

  $: tripVisiblePlacements = tripPlacements.slice(0, tripPrefixCount);
  $: tripRenderPlacements = tripDraggedPlacement
    ? [...tripVisiblePlacements, tripDraggedPlacement]
    : tripVisiblePlacements;
  $: tripSettleOutline =
    tripDraggedPlacement !== null ? tripDraggedPlacement.cells : [];
  $: tripUsedNames = new Set(tripVisiblePlacements.map((p) => p.name));
  $: tripAvailablePieces = triplicationProblem
    ? triplicationProblem.selectedPieces.filter((name) => !tripUsedNames.has(name))
    : [];
  $: if (tripSelectedPiece && tripUsedNames.has(tripSelectedPiece)) {
    tripSelectedPiece = tripAvailablePieces[0] ?? null;
  }
  $: tripTransformed = tripSelectedPiece ? cellsForPose(tripSelectedPiece, tripPose) : null;
  $: tripGhostPlacement =
    triplicationProblem && tripSelectedPiece && tripTransformed && tripHover && !tripDragActive
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
    clearRectangleSnapTimers();
    clearRectangleDragState();
    const target = event.currentTarget as HTMLSelectElement;
    selectedBoardSize = target.value as (typeof boardSizeOptions)[number];
    placements = [];
    prefixCount = 0;
    hover = null;
    selectedPiece = 'F';
    solvedSolutions = [];
    currentPrefixSolutions = null;
    activeSolverCountRequestId = -1;
    rectangleHoverPointerPos = null;
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

  function hasPlacementOverlap(cells: [number, number][], existing: Placement[]): boolean {
    const occupied = new Set(existing.flatMap((p) => p.cells.map(([r, c]) => `${r},${c}`)));
    return cells.some(([r, c]) => occupied.has(`${r},${c}`));
  }

  function pieceBarycenter(cells: [number, number][]): { row: number; col: number } {
    const count = cells.length || 1;
    const row = cells.reduce((sum, [r]) => sum + r + 0.5, 0) / count;
    const col = cells.reduce((sum, [, c]) => sum + c + 0.5, 0) / count;
    return { row, col };
  }

  function floatCellsAtPointerBarycenter(
    cells: [number, number][],
    pointerRow: number,
    pointerCol: number,
  ): [number, number][] {
    const center = pieceBarycenter(cells);
    const offsetRow = pointerRow - center.row;
    const offsetCol = pointerCol - center.col;
    return cells.map(([r, c]) => [r + offsetRow, c + offsetCol]);
  }

  function snappedPlacementAtPointerBarycenter(
    name: PieceName,
    cells: [number, number][],
    pointerRow: number,
    pointerCol: number,
  ): Placement {
    const center = pieceBarycenter(cells);
    const anchorRow = Math.round(pointerRow - center.row);
    const anchorCol = Math.round(pointerCol - center.col);
    return {
      name,
      cells: placeAtAnchor(cells, anchorRow, anchorCol),
    };
  }

  function cellsKey(cells: [number, number][]): string {
    return cells.map(([r, c]) => `${r.toFixed(3)},${c.toFixed(3)}`).join('|');
  }

  function clearRectangleGhostSnapAnimation(): void {
    if (rectangleGhostSnapRaf) {
      cancelAnimationFrame(rectangleGhostSnapRaf);
      rectangleGhostSnapRaf = 0;
    }
  }

  function setRectangleGhostSnapTarget(target: [number, number][]): void {
    const animSeq = ++rectangleGhostSnapAnimSeq;
    const targetKey = cellsKey(target);
    if (targetKey === rectangleGhostSnapTargetKey) {
      return;
    }
    rectangleGhostSnapTargetKey = targetKey;
    clearRectangleGhostSnapAnimation();
    if (target.length === 0) {
      rectangleGhostSnapOutline = [];
      return;
    }
    if (rectangleGhostSnapOutline.length !== target.length) {
      rectangleGhostSnapOutline = target.map(([r, c]) => [r, c] as [number, number]);
      return;
    }
    const from = rectangleGhostSnapOutline.map(([r, c]) => [r, c] as [number, number]);
    const to = target.map(([r, c]) => [r, c] as [number, number]);
    const startedAt = performance.now();
    const durationMs = 100;

    const animate = () => {
      if (animSeq !== rectangleGhostSnapAnimSeq) {
        return;
      }
      const elapsed = performance.now() - startedAt;
      const t = Math.max(0, Math.min(1, elapsed / durationMs));
      const eased = 1 - (1 - t) * (1 - t);
      rectangleGhostSnapOutline = from.map(([fr, fc], idx) => {
        const [tr, tc] = to[idx];
        return [fr + (tr - fr) * eased, fc + (tc - fc) * eased];
      });
      if (t < 1) {
        rectangleGhostSnapRaf = requestAnimationFrame(animate);
        return;
      }
      rectangleGhostSnapRaf = 0;
      rectangleGhostSnapOutline = to;
    };

    rectangleGhostSnapRaf = requestAnimationFrame(animate);
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

  function displayCellToViewportPoint(
    wrap: HTMLElement | null,
    row: number,
    col: number,
    displayRows: number,
    displayCols: number,
  ): ViewportPoint | null {
    if (!wrap || displayRows <= 0 || displayCols <= 0) {
      return null;
    }
    const rect = wrap.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    return {
      x: rect.left + ((col + 0.5) / displayCols) * rect.width,
      y: rect.top + ((row + 0.5) / displayRows) * rect.height,
    };
  }

  function runStatusFlight(
    text: string,
    from: ViewportPoint | null,
    target: HTMLElement | null,
  ): boolean {
    if (!target) {
      return false;
    }
    const rect = target.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return false;
    }
    const start = sanitizeViewportPoint(from) ?? {
      x: rect.left + rect.width * 0.5,
      y: rect.top + rect.height * 0.5,
    };
    if (statusFlightTimer) {
      clearTimeout(statusFlightTimer);
      statusFlightTimer = null;
    }
    const targetX = rect.left + 12;
    const targetY = rect.top + rect.height / 2;
    const id = ++statusFlightSeq;
    statusFlight = {
      id,
      text,
      x: start.x,
      y: start.y,
      dx: targetX - start.x,
      dy: targetY - start.y,
      active: false,
    };
    requestAnimationFrame(() => {
      if (!statusFlight || statusFlight.id !== id) {
        return;
      }
      statusFlight = { ...statusFlight, active: true };
    });
    statusFlightTimer = setTimeout(() => {
      if (statusFlight && statusFlight.id === id) {
        statusFlight = null;
      }
      statusFlightTimer = null;
    }, STATUS_FLIGHT_MS + 20);
    return true;
  }

  function elementCenterPoint(el: HTMLElement | null): ViewportPoint | null {
    if (!el) {
      return null;
    }
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    return {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
    };
  }

  function sanitizeViewportPoint(point: ViewportPoint | null): ViewportPoint | null {
    if (!point) {
      return null;
    }
    if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) {
      return null;
    }
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (vw <= 0 || vh <= 0) {
      return null;
    }
    const x = Math.max(0, Math.min(vw, point.x));
    const y = Math.max(0, Math.min(vh, point.y));
    if (x <= 1 && y <= 1) {
      return null;
    }
    return { x, y };
  }

  function pointForBoardEvent(
    x: number,
    y: number,
    boardWrap: HTMLElement | null,
    displayRow: number,
    displayCol: number,
    displayRows: number,
    displayCols: number,
  ): ViewportPoint | null {
    const direct = sanitizeViewportPoint({ x, y });
    if (direct) {
      return direct;
    }
    const cellCenter = displayCellToViewportPoint(
      boardWrap,
      displayRow,
      displayCol,
      displayRows,
      displayCols,
    );
    if (cellCenter) {
      return sanitizeViewportPoint(cellCenter);
    }
    return sanitizeViewportPoint(elementCenterPoint(boardWrap));
  }

  function setRectangleStatusWithFlight(
    text: string,
    from: ViewportPoint | null,
  ): void {
    if (rectangleStatusDelayTimer) {
      clearTimeout(rectangleStatusDelayTimer);
      rectangleStatusDelayTimer = null;
    }
    const fallbackFrom = from ?? elementCenterPoint(rectangleBoardWrapEl);
    if (!runStatusFlight(text, fallbackFrom, rectangleStatusEl)) {
      status = text;
      return;
    }
    rectangleStatusDelayTimer = setTimeout(() => {
      status = text;
      rectangleStatusDelayTimer = null;
    }, STATUS_FLIGHT_MS);
  }

  function setTripStatusWithFlight(
    text: string,
    from: ViewportPoint | null,
  ): void {
    if (tripStatusDelayTimer) {
      clearTimeout(tripStatusDelayTimer);
      tripStatusDelayTimer = null;
    }
    const fallbackFrom = from ?? elementCenterPoint(tripBoardWrapEl);
    if (!runStatusFlight(text, fallbackFrom, tripStatusEl)) {
      triplicationStatus = text;
      return;
    }
    tripStatusDelayTimer = setTimeout(() => {
      triplicationStatus = text;
      tripStatusDelayTimer = null;
    }, STATUS_FLIGHT_MS);
  }

  function clearSolverAfterSolved(message: string): void {
    if (rectangleSolvedTransitionTimer) {
      clearTimeout(rectangleSolvedTransitionTimer);
      rectangleSolvedTransitionTimer = null;
    }
    placements = [];
    prefixCount = 0;
    hover = null;
    rectangleHoverPointerPos = null;
    selectedPiece = 'F';
    resetPose();
    status = message;
    currentPrefixSolutions = null;
    activeSolverCountRequestId = -1;
    clearRectangleDragState();
    clearRectangleSnapTimers();
  }

  function clearTripSolverAfterSolved(message: string): void {
    if (!triplicationProblem) {
      return;
    }
    if (tripSolvedTransitionTimer) {
      clearTimeout(tripSolvedTransitionTimer);
      tripSolvedTransitionTimer = null;
    }
    tripPlacements = [];
    tripPrefixCount = 0;
    tripHover = null;
    tripSelectedPiece = triplicationProblem.selectedPieces[0] ?? null;
    tripResetPose();
    triplicationStatus = message;
    tripDraggedPlacement = null;
  }

  function solvedTransitionStyleFor(source: HTMLElement | null): string | null {
    if (!source || !solvedToggleEl) {
      return null;
    }
    const sourceRect = source.getBoundingClientRect();
    const targetRect = solvedToggleEl.getBoundingClientRect();
    if (sourceRect.width === 0 || sourceRect.height === 0 || targetRect.width === 0 || targetRect.height === 0) {
      return null;
    }
    const sourceX = sourceRect.left + sourceRect.width / 2;
    const sourceY = sourceRect.top + sourceRect.height / 2;
    const targetX = targetRect.left + targetRect.width / 2;
    const targetY = targetRect.top + targetRect.height / 2;
    const scale = Math.max(0.08, Math.min(targetRect.width / sourceRect.width, targetRect.height / sourceRect.height));
    return `--solved-dx:${targetX - sourceX}px;--solved-dy:${targetY - sourceY}px;--solved-scale:${scale};`;
  }

  function switchToSolvedViewAfterRectangleSolve(message: string): void {
    if (!useTouchLayout) {
      clearSolverAfterSolved(message);
      return;
    }

    const transitionStyle = solvedTransitionStyleFor(rectangleBoardWrapEl);
    if (!transitionStyle) {
      clearSolverAfterSolved(message);
      touchViewMode = 'solved';
      return;
    }

    rectangleSolvedTransitionStyle = transitionStyle;
    rectangleSolvedTransitioning = true;
    rectangleSolvedTransitionTimer = setTimeout(() => {
      rectangleSolvedTransitioning = false;
      rectangleSolvedTransitionStyle = '';
      clearSolverAfterSolved(message);
      touchViewMode = 'solved';
      rectangleSolvedTransitionTimer = null;
    }, SOLVED_TRANSITION_MS);
  }

  function switchToSolvedViewAfterTriplicationSolve(message: string): void {
    if (!useTouchLayout) {
      clearTripSolverAfterSolved(message);
      return;
    }

    const transitionStyle = solvedTransitionStyleFor(tripBoardWrapEl);
    if (!transitionStyle) {
      clearTripSolverAfterSolved(message);
      touchViewMode = 'solved';
      return;
    }

    tripSolvedTransitionStyle = transitionStyle;
    tripSolvedTransitioning = true;
    tripSolvedTransitionTimer = setTimeout(() => {
      tripSolvedTransitioning = false;
      tripSolvedTransitionStyle = '';
      clearTripSolverAfterSolved(message);
      touchViewMode = 'solved';
      tripSolvedTransitionTimer = null;
    }, SOLVED_TRANSITION_MS);
  }

  function requestSolverPrefixCount(snapshot: Placement[], rows: number, cols: number): void {
    if (!solverCountWorker) {
      return;
    }
    const requestId = ++solverCountRequestSeq;
    activeSolverCountRequestId = requestId;
    solverCountWorker.postMessage({
      requestId,
      placements: snapshot,
      rows,
      cols,
      limit: 200,
    });
  }

  function clearRectangleSnapTimers(): void {
    if (rectangleSnapTimer) {
      clearTimeout(rectangleSnapTimer);
      rectangleSnapTimer = null;
    }
    if (rectangleSnapRaf) {
      cancelAnimationFrame(rectangleSnapRaf);
      rectangleSnapRaf = 0;
    }
  }

  function rectangleBoardPosFromClient(
    clientX: number,
    clientY: number,
    clampToBoard: boolean,
  ): { row: number; col: number } | null {
    if (!rectangleBoardWrapEl) {
      return null;
    }
    const rect = rectangleBoardWrapEl.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    let x = clientX - rect.left;
    let y = clientY - rect.top;
    if (clampToBoard) {
      x = Math.max(0, Math.min(rect.width, x));
      y = Math.max(0, Math.min(rect.height, y));
    }
    if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
      return null;
    }
    const displayRow = (y / rect.height) * rectangleDisplayRows;
    const displayCol = (x / rect.width) * rectangleDisplayCols;
    const [row, col] = fromDisplayCell(
      displayRow,
      displayCol,
      boardRows,
      rectangleBoardRotatedView,
    );
    return { row, col };
  }

  function updateRectangleTouchOverlayStyle(): void {
    if (!paneTabsEl || !rectangleBoardWrapEl) {
      rectangleTouchOverlayStyle = '';
      return;
    }
    const tabsRect = paneTabsEl.getBoundingClientRect();
    const boardRect = rectangleBoardWrapEl.getBoundingClientRect();
    const top = Math.ceil(tabsRect.bottom + 1);
    const height = Math.max(0, Math.floor(boardRect.top - tabsRect.bottom - 2));
    rectangleTouchOverlayStyle =
      `top:${top}px;left:${Math.round(boardRect.left)}px;` +
      `width:${Math.round(boardRect.width)}px;height:${height}px;`;
  }

  function rectangleOverlayPosFromClient(
    clientX: number,
    clientY: number,
  ): { row: number; col: number } | null {
    if (!rectangleTouchOverlayEl) {
      return null;
    }
    const rect = rectangleTouchOverlayEl.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, clientY - rect.top));
    const displayRow = (y / rect.height) * rectangleDisplayRows;
    const displayCol = (x / rect.width) * rectangleDisplayCols;
    const [row, col] = fromDisplayCell(
      displayRow,
      displayCol,
      boardRows,
      rectangleBoardRotatedView,
    );
    return { row, col };
  }

  function applyRectanglePickerDragPointer(
    clientX: number,
    clientY: number,
    clampToBoard: boolean,
  ): void {
    rectanglePickerPointerClient = { x: clientX, y: clientY };
    const boardPos = rectangleBoardPosFromClient(clientX, clientY, clampToBoard);
    const overlayPos = rectangleOverlayPosFromClient(clientX, clientY);
    const visualPos = boardPos ?? overlayPos;
    if (selectedPiece && transformed && visualPos) {
      rectangleFloatingPlacement = {
        name: selectedPiece,
        cells: floatCellsAtPointerBarycenter(
          transformed,
          visualPos.row,
          visualPos.col,
        ),
      };
    }
    if (!boardPos) {
      rectangleHoverPointerPos = null;
      rectanglePointerOverBoard = false;
      rectangleDraggedPlacement = null;
      rectangleDraggedPlacementValid = false;
      return;
    }
    rectanglePointerOverBoard = true;
    rectangleHoverPointerPos = boardPos;
    setRectangleDragCandidateFromPointer(boardPos.row, boardPos.col, false);
    rectangleDragMoved = true;
  }

  function onPickerPointerMove(event: PointerEvent): void {
    if (!rectanglePickerDrag || event.pointerId !== rectanglePickerDrag.pointerId) {
      return;
    }
    event.preventDefault();
    applyRectanglePickerDragPointer(event.clientX, event.clientY, true);
  }

  function finalizeRectanglePickerDrag(dropOnBoard: boolean): void {
    if (!rectanglePickerDrag) {
      return;
    }
    const dragged = rectanglePickerDrag;
    if (!dropOnBoard || !rectangleDraggedPlacement || !rectangleDraggedPlacementValid) {
      rectangleDragActive = false;
      rectanglePickerDrag = null;
      rectangleDragPointerType = null;
      rectangleHoverPointerPos = null;
      rectanglePointerOverBoard = false;
      rectangleDraggedPlacement = null;
      rectangleDraggedPlacementValid = false;
      rectangleFloatingPlacement = null;
      rectanglePickerPointerClient = null;
      return;
    }
    const candidate = clonePlacements([rectangleDraggedPlacement])[0];
    rectangleDragActive = false;
    rectanglePickerDrag = null;
    rectangleDragPointerType = null;
    rectangleHoverPointerPos = null;
    rectanglePointerOverBoard = false;
    rectangleDraggedPlacement = null;
    rectangleDraggedPlacementValid = false;
    rectangleFloatingPlacement = null;
    rectanglePickerPointerClient = null;
    if (!commitPlacement(candidate)) {
      status = `Cannot place ${dragged.piece} there.`;
    }
  }

  function onPickerPointerUp(event: PointerEvent): void {
    if (!rectanglePickerDrag || event.pointerId !== rectanglePickerDrag.pointerId) {
      return;
    }
    event.preventDefault();
    const boardPos = rectangleBoardPosFromClient(event.clientX, event.clientY, false);
    if (boardPos) {
      applyRectanglePickerDragPointer(event.clientX, event.clientY, true);
    }
    finalizeRectanglePickerDrag(!!boardPos);
  }

  function onPickerPointerCancel(event: PointerEvent): void {
    if (!rectanglePickerDrag || event.pointerId !== rectanglePickerDrag.pointerId) {
      return;
    }
    event.preventDefault();
    finalizeRectanglePickerDrag(false);
  }

  function startPickerDrag(event: PointerEvent, piece: PieceName): void {
    const pointerType = event.pointerType || 'touch';
    if (isRectangleLocked || pointerType !== 'touch') {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (selectedPiece !== piece) {
      selectedPiece = piece;
      resetPose();
    }
    rectanglePickerDrag = {
      pointerId: event.pointerId,
      pointerType,
      piece,
    };
    rectangleDragPointerType = pointerType;
    rectangleDragActive = true;
    rectangleDraggedOriginPlacement = null;
    rectangleDraggedOriginKey = null;
    rectangleDragStartCells = null;
    rectangleDragStartPointer = null;
    rectangleDragMoved = false;
    rectangleDraggedPlacement = null;
    rectangleDraggedPlacementValid = false;
    rectangleFloatingPlacement = null;
    hover = null;
    rectangleHoverPointerPos = null;
    rectanglePointerOverBoard = false;
    applyRectanglePickerDragPointer(event.clientX, event.clientY, true);
  }

  function clearRectangleDragState(): void {
    rectangleDraggedPlacement = null;
    rectangleDraggedOriginPlacement = null;
    rectangleDraggedOriginKey = null;
    rectangleDraggedPlacementValid = false;
    rectangleDragMoved = false;
    rectangleSnapAnimating = false;
    rectangleFloatingPlacement = null;
    rectanglePointerPos = null;
    rectangleDragStartPointer = null;
    rectangleDragStartCells = null;
    rectanglePointerOverBoard = false;
    rectangleDragPointerType = null;
    rectanglePickerDrag = null;
    rectanglePickerPointerClient = null;
    clearRectangleGhostSnapAnimation();
    rectangleGhostSnapOutline = [];
    rectangleGhostSnapTargetKey = '';
  }

  function restoreRectangleDragOrigin(): void {
    clearRectangleDragState();
  }

  function startRectangleSnapFinalize(): void {
    if (rectangleSnapAnimating || !rectangleDraggedPlacement) {
      return;
    }
    if (!rectangleDraggedPlacementValid) {
      if (rectangleDraggedOriginPlacement) {
        finalizeRectangleRemoval(rectangleDraggedOriginPlacement);
      } else {
        restoreRectangleDragOrigin();
      }
      return;
    }
    rectangleSnapAnimating = true;
    const candidate = clonePlacements([rectangleDraggedPlacement])[0];
    const startCells =
      rectangleFloatingPlacement?.cells.map(([r, c]) => [r, c] as [number, number]) ??
      candidate.cells.map(([r, c]) => [r, c] as [number, number]);
    const endCells = candidate.cells.map(([r, c]) => [r, c] as [number, number]);
    const startedAt = performance.now();
    const durationMs = 100;

    const animate = () => {
      const elapsed = performance.now() - startedAt;
      const t = Math.max(0, Math.min(1, elapsed / durationMs));
      const eased = 1 - (1 - t) * (1 - t);
      rectangleFloatingPlacement = {
        name: candidate.name,
        cells: startCells.map(([sr, sc], idx) => {
          const [er, ec] = endCells[idx];
          return [sr + (er - sr) * eased, sc + (ec - sc) * eased];
        }),
      };
      if (t < 1) {
        rectangleSnapRaf = requestAnimationFrame(animate);
        return;
      }
      rectangleSnapRaf = 0;
      rectangleSnapAnimating = false;
      finalizeRectangleCommit(candidate);
    };

    rectangleSnapRaf = requestAnimationFrame(animate);
  }

  function setRectangleDragCandidateFromPointer(
    pointerRow: number,
    pointerCol: number,
    updateFloating = true,
  ): void {
    if (!selectedPiece || !transformed) {
      return;
    }
    let candidate: Placement;
    if (rectangleDragStartPointer && rectangleDragStartCells) {
      const deltaRow = pointerRow - rectangleDragStartPointer.row;
      const deltaCol = pointerCol - rectangleDragStartPointer.col;
      const floatCells = rectangleDragStartCells.map(([r, c]) =>
        [r + deltaRow, c + deltaCol] as [number, number],
      );
      if (updateFloating) {
        rectangleFloatingPlacement = { name: selectedPiece, cells: floatCells };
      }
      const snapDeltaRow = Math.round(deltaRow);
      const snapDeltaCol = Math.round(deltaCol);
      candidate = {
        name: selectedPiece,
        cells: rectangleDragStartCells.map(([r, c]) =>
          [r + snapDeltaRow, c + snapDeltaCol] as [number, number],
        ),
      };
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('pento:drag-sample', {
            detail: {
              deltaRow,
              deltaCol,
              snapDeltaRow,
              snapDeltaCol,
            },
          }),
        );
      }
    } else {
      const floatCells = transformed.map(([r, c]) =>
        [r + pointerRow, c + pointerCol] as [number, number],
      );
      if (updateFloating) {
        rectangleFloatingPlacement = { name: selectedPiece, cells: floatCells };
      }
      candidate = snappedPlacementAtPointerBarycenter(
        selectedPiece,
        transformed,
        pointerRow,
        pointerCol,
      );
    }

    const candidateKey = solutionKey([{ name: candidate.name, cells: candidate.cells }]);
    if (rectangleDraggedOriginKey && candidateKey !== rectangleDraggedOriginKey) {
      rectangleDragMoved = true;
    }
    rectangleDraggedPlacementValid =
      inBoundsForBoard(candidate.cells) &&
      canApplyPlacement(rectangleBasePlacements, candidate, boardRows, boardCols);
    rectangleDraggedPlacement = clonePlacements([candidate])[0];
  }

  function commitPlacement(candidate: Placement): boolean {
    if (isRectangleLocked) {
      return false;
    }
    if (!inBoundsForBoard(candidate.cells) || !canApplyPlacement(visiblePlacements, candidate, boardRows, boardCols)) {
      return false;
    }
    truncateToPrefix();
    placements = [...placements, clonePlacements([candidate])[0]];
    prefixCount = placements.length;

    if (placements.length === PIECE_ORDER.length) {
      addSolved(placements);
      switchToSolvedViewAfterRectangleSolve('Rectangle solved manually. Added to Solved; Solver cleared.');
      return true;
    }

    currentPrefixSolutions = null;
    status = `${candidate.name} placed. Counting solutions for this prefix...`;
    requestSolverPrefixCount(clonePlacements(placements), boardRows, boardCols);
    return true;
  }

  function finalizeRectangleCommit(candidate: Placement): void {
    const next = [...rectangleBasePlacements, clonePlacements([candidate])[0]];
    placements = clonePlacements(next);
    prefixCount = placements.length;
    selectedPiece = null;
    clearRectangleDragState();

    if (placements.length === PIECE_ORDER.length) {
      addSolved(placements);
      switchToSolvedViewAfterRectangleSolve('Rectangle solved manually. Added to Solved; Solver cleared.');
      return;
    }

    currentPrefixSolutions = null;
    status = `${candidate.name} placed. Counting solutions for this prefix...`;
    requestSolverPrefixCount(clonePlacements(placements), boardRows, boardCols);
  }

  function finalizeRectangleRemoval(origin: Placement): void {
    const next = visiblePlacements.filter((p) => p.name !== origin.name);
    placements = clonePlacements(next);
    prefixCount = placements.length;
    clearRectangleDragState();
    currentPrefixSolutions = null;
    activeSolverCountRequestId = -1;
    status = `${origin.name} removed and selected. Counting solutions for this prefix...`;
    requestSolverPrefixCount(clonePlacements(placements), boardRows, boardCols);
  }

  function placementAtCell(row: number, col: number): Placement | null {
    if (!selectedPiece || !transformed) {
      return null;
    }
    return snappedPlacementAtPointerBarycenter(
      selectedPiece,
      transformed,
      row + 0.5,
      col + 0.5,
    );
  }

  function isOccupiedCell(placementsSnapshot: Placement[], row: number, col: number): boolean {
    return placementsSnapshot.some((p) => p.cells.some(([r, c]) => r === row && c === col));
  }

  function removePieceAt(row: number, col: number): boolean {
    if (isRectangleLocked) {
      return false;
    }
    const hit = visiblePlacements.find((p) => p.cells.some(([r, c]) => r === row && c === col));
    if (!hit) {
      return false;
    }
    const dragged = clonePlacements([hit])[0];
    rectangleDraggedOriginKey = solutionKey([{ name: dragged.name, cells: dragged.cells }]);
    rectangleDraggedOriginPlacement = clonePlacements([dragged])[0];
    rectangleDragMoved = false;
    rectangleDraggedPlacementValid = true;
    selectedPiece = hit.name;
    resetPose();
    hover = null;
    rectangleHoverPointerPos = null;
    currentPrefixSolutions = null;
    activeSolverCountRequestId = -1;
    rectangleDraggedPlacement = dragged;
    rectangleFloatingPlacement = {
      name: dragged.name,
      cells: dragged.cells.map(([r, c]) => [r, c] as [number, number]),
    };
    rectangleDragStartPointer = rectangleHoverPointerPos ?? { row: row + 0.5, col: col + 0.5 };
    rectangleDragStartCells = dragged.cells.map(([r, c]) => [r, c] as [number, number]);
    rectanglePointerPos = { row, col };
    status = `${hit.name} removed and selected.`;
    return true;
  }

  function onBoardClick(
    event: CustomEvent<{ row: number; col: number; x: number; y: number }>,
  ): void {
    if (isRectangleLocked) {
      return;
    }
    const [row, col] = fromDisplayCell(
      event.detail.row,
      event.detail.col,
      boardRows,
      rectangleBoardRotatedView,
    );
    const clickPoint = pointForBoardEvent(
      event.detail.x,
      event.detail.y,
      rectangleBoardWrapEl,
      event.detail.row,
      event.detail.col,
      rectangleDisplayRows,
      rectangleDisplayCols,
    );
    hover = { row, col };
    if (removePieceAt(row, col)) {
      return;
    }
    const pointer = rectangleHoverPointerPos ?? { row: row + 0.5, col: col + 0.5 };
    const candidate =
      selectedPiece && transformed
        ? snappedPlacementAtPointerBarycenter(
            selectedPiece,
            transformed,
            pointer.row,
            pointer.col,
          )
        : placementAtCell(row, col);
    if (!candidate) {
      return;
    }
    if (!commitPlacement(candidate)) {
      setRectangleStatusWithFlight('Cannot place piece there.', clickPoint);
    }
  }

  function onBoardDrop(event: CustomEvent<{ row: number; col: number } | null>): void {
    if (isRectangleLocked) {
      return;
    }
    if (!rectangleDraggedOriginPlacement) {
      return;
    }
    rectangleHoverPointerPos = null;
    if (!event.detail) {
      hover = null;
      finalizeRectangleRemoval(rectangleDraggedOriginPlacement);
      clearRectangleSnapTimers();
      return;
    }
    const [row, col] = fromDisplayCell(
      event.detail.row,
      event.detail.col,
      boardRows,
      rectangleBoardRotatedView,
    );
    rectanglePointerPos = { row, col };
    hover = isOccupiedCell(visiblePlacements, row, col) ? null : { row, col };
    if (hover) {
      setRectangleDragCandidateFromPointer(hover.row, hover.col);
    }
    if (!rectangleDragMoved) {
      finalizeRectangleRemoval(rectangleDraggedOriginPlacement);
      clearRectangleSnapTimers();
      return;
    }
    if (!rectangleDraggedPlacementValid) {
      finalizeRectangleRemoval(rectangleDraggedOriginPlacement);
      clearRectangleSnapTimers();
      return;
    }
    if (!rectangleDraggedPlacement) {
      finalizeRectangleRemoval(rectangleDraggedOriginPlacement);
      clearRectangleSnapTimers();
      return;
    }
    startRectangleSnapFinalize();
  }

  function onRectangleDragState(
    event: CustomEvent<{ active: boolean; pointerType: string | null }>,
  ): void {
    rectangleDragActive = event.detail.active;
    rectangleDragPointerType = event.detail.pointerType;
    if (!rectangleDragActive) {
      rectangleHoverPointerPos = null;
      setRectangleGhostSnapTarget([]);
    }
  }

  function solveNow(): void {
    if (isRectangleLocked) {
      return;
    }
    clearRectangleSnapTimers();
    clearRectangleDragState();
    activeSolverCountRequestId = -1;
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
    switchToSolvedViewAfterRectangleSolve('Solved from current state. Added to Solved; Solver cleared.');
  }

  function importSolved(index: number): void {
    if (isRectangleLocked) {
      return;
    }
    clearRectangleSnapTimers();
    clearRectangleDragState();
    const chosen = solvedSolutions[index];
    selectedBoardSize = `${chosen.cols}x${chosen.rows}` as (typeof boardSizeOptions)[number];
    placements = clonePlacements(chosen.placements);
    prefixCount = chosen.placements.length;
    selectedPiece = null;
    currentPrefixSolutions = null;
    activeSolverCountRequestId = -1;
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

  function importTripSolved(index: number): void {
    if (isTriplicationLocked) {
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
      if (!triplicationProblem || isTriplicationLocked) {
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

    if (isRectangleLocked) {
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
      rectangleHoverPointerPos = null;
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
    if (isRectangleLocked) {
      return;
    }
    if (!event.detail) {
      hover = null;
      rectanglePointerOverBoard = false;
      rectangleHoverPointerPos = null;
      if (rectangleDragActive && rectangleDraggedOriginPlacement) {
        rectangleDraggedPlacement = null;
        rectangleDraggedPlacementValid = false;
      }
      return;
    }
    const [row, col] = fromDisplayCell(
      event.detail.row,
      event.detail.col,
      boardRows,
      rectangleBoardRotatedView,
    );
    hover = isOccupiedCell(visiblePlacements, row, col) ? null : { row, col };
    rectanglePointerOverBoard = true;
    if (!hover) {
      rectangleHoverPointerPos = null;
    }
  }

  function onRectanglePointerMove(
    event: CustomEvent<{ row: number; col: number } | null>,
  ): void {
    if (!event.detail) {
      if (!rectangleDragActive) {
        rectangleHoverPointerPos = null;
      }
      return;
    }
    const [row, col] = fromDisplayCell(
      event.detail.row,
      event.detail.col,
      boardRows,
      rectangleBoardRotatedView,
    );
    if (!rectangleDragActive || !rectangleDraggedOriginPlacement) {
      if (rectangleDragActive && !rectangleDraggedOriginPlacement) {
        rectangleHoverPointerPos = { row, col };
        return;
      }
      if (!rectangleDragActive && rectangleDraggedOriginPlacement) {
        rectangleHoverPointerPos = null;
        return;
      }
      const cellRow = Math.floor(row);
      const cellCol = Math.floor(col);
      if (isOccupiedCell(visiblePlacements, cellRow, cellCol)) {
        rectangleHoverPointerPos = null;
        return;
      }
      rectangleHoverPointerPos = { row, col };
      return;
    }
    if (!rectanglePointerOverBoard) {
      rectangleDraggedPlacement = null;
      rectangleDraggedPlacementValid = false;
      return;
    }
    rectanglePointerPos = { row, col };
    setRectangleDragCandidateFromPointer(row, col);
  }

  function sliderChanged(value: number): void {
    clearRectangleSnapTimers();
    clearRectangleDragState();
    prefixCount = Math.max(0, Math.min(value, placements.length));
    currentPrefixSolutions = null;
    activeSolverCountRequestId = -1;
    status = `${prefixCount} pentominoes fixed in Solver.`;
  }

  function onSliderInput(event: Event): void {
    if (isRectangleLocked) {
      return;
    }
    const target = event.currentTarget as HTMLInputElement;
    sliderChanged(Number(target.value));
  }

  function onInitialSpeedInput(event: Event): void {
    if (isRectangleLocked) {
      return;
    }
    const target = event.currentTarget as HTMLInputElement;
    speedSlider = Number(target.value);
  }

  function onTripInitialSpeedInput(event: Event): void {
    if (isTriplicationLocked) {
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

  function resetToLongestValidPrefix(sourceEl: HTMLElement | null = null): void {
    clearRectangleSnapTimers();
    clearRectangleDragState();
    const longest = longestValidPrefix(clonePlacements(visiblePlacements));
    placements = clonePlacements(longest);
    prefixCount = longest.length;
    currentPrefixSolutions = null;
    activeSolverCountRequestId = -1;
    setRectangleStatusWithFlight(
      `Reset to longest valid prefix (${longest.length} pieces).`,
      elementCenterPoint(sourceEl),
    );
  }

  function onResetStatusActionClick(event: MouseEvent): void {
    const sourceEl = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
    resetToLongestValidPrefix(sourceEl);
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
    if (isTriplicationLocked) {
      return;
    }
    tripSelectedPiece = name;
    tripResetPose();
  }

  function commitTripPlacement(candidate: Placement): boolean {
    if (!triplicationProblem || isTriplicationLocked) {
      return false;
    }
    if (!canApplyTriplicationPlacement(triplicationProblem, tripVisiblePlacements, candidate)) {
      return false;
    }
    if (tripPrefixCount < tripPlacements.length) {
      tripPlacements = tripPlacements.slice(0, tripPrefixCount);
    }
    tripPlacements = [...tripPlacements, clonePlacements([candidate])[0]];
    tripPrefixCount = tripPlacements.length;
    if (tripPlacements.length === triplicationProblem.selectedPieces.length) {
      addTripSolved(triplicationProblem, tripPlacements);
      switchToSolvedViewAfterTriplicationSolve('Triplication solved manually. Added to Solved; Solver cleared.');
      return true;
    }
    triplicationStatus = `${candidate.name} placed on triplication board.`;
    return true;
  }

  function removeTripPieceAt(row: number, col: number): boolean {
    const hit = tripVisiblePlacements.find((p) => p.cells.some(([r, c]) => r === row && c === col));
    if (!hit) {
      return false;
    }
    const dragged = clonePlacements([hit])[0];
    tripPlacements = tripVisiblePlacements.filter((p) => p.name !== hit.name);
    tripPrefixCount = tripPlacements.length;
    tripSelectedPiece = hit.name;
    tripResetPose();
    tripHover = null;
    tripDraggedPlacement = tripDragActive ? dragged : null;
    triplicationStatus = `${hit.name} removed and selected.`;
    return true;
  }

  function onTripBoardHover(event: CustomEvent<{ row: number; col: number } | null>): void {
    if (isTriplicationLocked) {
      return;
    }
    if (!event.detail) {
      tripHover = null;
      return;
    }
    tripHover = isOccupiedCell(tripVisiblePlacements, event.detail.row, event.detail.col) ? null : event.detail;
  }

  function onTripBoardClick(
    event: CustomEvent<{ row: number; col: number; x: number; y: number }>,
  ): void {
    if (isTriplicationLocked || !triplicationProblem) {
      return;
    }
    const { row, col } = event.detail;
    const clickPoint = pointForBoardEvent(
      event.detail.x,
      event.detail.y,
      tripBoardWrapEl,
      row,
      col,
      triplicationProblem.rows,
      triplicationProblem.cols,
    );
    tripHover = { row, col };
    if (removeTripPieceAt(row, col)) {
      return;
    }
    if (!tripSelectedPiece || !tripTransformed) {
      return;
    }
    if (!commitTripPlacement({ name: tripSelectedPiece, cells: placeAtAnchor(tripTransformed, row, col) })) {
      setTripStatusWithFlight('Cannot place piece there.', clickPoint);
    }
  }

  function onTripBoardDrop(event: CustomEvent<{ row: number; col: number } | null>): void {
    if (isTriplicationLocked || !triplicationProblem) {
      return;
    }
    if (!event.detail) {
      tripDraggedPlacement = null;
      return;
    }
    tripDraggedPlacement = null;
    const { row, col } = event.detail;
    if (isOccupiedCell(tripVisiblePlacements, row, col)) {
      tripHover = null;
      return;
    }
    tripHover = { row, col };
    if (!tripSelectedPiece || !tripTransformed) {
      return;
    }
    commitTripPlacement({ name: tripSelectedPiece, cells: placeAtAnchor(tripTransformed, row, col) });
  }

  function onTripDragState(event: CustomEvent<{ active: boolean }>): void {
    tripDragActive = event.detail.active;
    if (!tripDragActive) {
      tripDraggedPlacement = null;
    }
  }

  function solveTriplicationNow(): void {
    if (!triplicationProblem || isTriplicationLocked) {
      return;
    }
    const solved = solveTriplicationFromPlacements(triplicationProblem, clonePlacements(tripVisiblePlacements), 400000);
    if (!solved) {
      triplicationStatus = 'No completion found from the current triplication prefix.';
      return;
    }
    addTripSolved(triplicationProblem, solved);
    switchToSolvedViewAfterTriplicationSolve('Triplication solved from current state. Added to Solved; Solver cleared.');
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
        switchToSolvedViewAfterTriplicationSolve('Triplication animation complete. Added to Solved; Solver cleared.');
      }
    }, 100);
  }

  function onTripSliderInput(event: Event): void {
    if (isTriplicationLocked) {
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
    activeSolverCountRequestId = -1;
  }

  function animateSolve(): void {
    if (rectangleSolvedTransitioning) {
      return;
    }
    if (isAnimating) {
      stopAnimationAtCurrentStage();
      return;
    }
    activeSolverCountRequestId = -1;

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
        switchToSolvedViewAfterRectangleSolve('Animated solve complete. Added to Solved; Solver cleared.');
      }
    }, 100);
  }

  function toggleTouchViewMode(): void {
    if (!useTouchLayout) {
      return;
    }
    if (rectangleSolvedTransitioning || tripSolvedTransitioning) {
      return;
    }
    touchViewMode = touchViewMode === 'solver' ? 'solved' : 'solver';
  }

  onDestroy(() => {
    stopAnimationTimer();
    stopTripAnimationTimer();
    if (rectangleSolvedTransitionTimer) {
      clearTimeout(rectangleSolvedTransitionTimer);
    }
    if (tripSolvedTransitionTimer) {
      clearTimeout(tripSolvedTransitionTimer);
    }
    clearRectangleSnapTimers();
    clearRectangleDragState();
    if (rectangleStatusDelayTimer) {
      clearTimeout(rectangleStatusDelayTimer);
      rectangleStatusDelayTimer = null;
    }
    if (tripStatusDelayTimer) {
      clearTimeout(tripStatusDelayTimer);
      tripStatusDelayTimer = null;
    }
    if (statusFlightTimer) {
      clearTimeout(statusFlightTimer);
      statusFlightTimer = null;
    }
    statusFlight = null;
    solverCountWorker?.terminate();
    solverCountWorker = null;
    if (typeof window !== 'undefined') {
      window.removeEventListener('pointermove', onPickerPointerMove);
      window.removeEventListener('pointerup', onPickerPointerUp);
      window.removeEventListener('pointercancel', onPickerPointerCancel);
      window.removeEventListener('resize', updateRectangleTouchOverlayStyle);
      window.removeEventListener('scroll', updateRectangleTouchOverlayStyle, true);
    }
  });

  onMount(() => {
    const updateLayoutMode = () => {
      useTouchLayout =
        isTouchDevice ||
        window.innerWidth <= COMPACT_LAYOUT_MAX_WIDTH;
      if (!useTouchLayout) {
        touchViewMode = 'solver';
      }
    };
    updateLayoutMode();
    window.addEventListener('resize', updateLayoutMode);
    window.addEventListener('pointermove', onPickerPointerMove, { passive: false });
    window.addEventListener('pointerup', onPickerPointerUp, { passive: false });
    window.addEventListener('pointercancel', onPickerPointerCancel, { passive: false });
    window.addEventListener('resize', updateRectangleTouchOverlayStyle);
    window.addEventListener('scroll', updateRectangleTouchOverlayStyle, true);
    updateRectangleTouchOverlayStyle();

    solverCountWorker = new Worker(new URL('./lib/solverCount.worker.ts', import.meta.url), { type: 'module' });
    solverCountWorker.onmessage = (event: MessageEvent<SolverCountResponse>) => {
      const { requestId, count, complete } = event.data;
      if (requestId !== activeSolverCountRequestId) {
        return;
      }
      currentPrefixSolutions = count;
      const noun = count === 1 ? 'solution' : 'solutions';
      const placedName = placements[prefixCount - 1]?.name;
      status = `${placedName ?? 'Piece'} placed. ${count} ${noun} for this prefix${complete ? '' : ' and counting'}.`;
    };
    solverCountWorker.onerror = () => {
      if (activeSolverCountRequestId === -1) {
        return;
      }
      activeSolverCountRequestId = -1;
      currentPrefixSolutions = null;
      status = 'Could not count prefix solutions in background.';
    };
    newTriplicationProblem();

    return () => {
      window.removeEventListener('resize', updateLayoutMode);
      window.removeEventListener('pointermove', onPickerPointerMove);
      window.removeEventListener('pointerup', onPickerPointerUp);
      window.removeEventListener('pointercancel', onPickerPointerCancel);
      window.removeEventListener('resize', updateRectangleTouchOverlayStyle);
      window.removeEventListener('scroll', updateRectangleTouchOverlayStyle, true);
    };
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

<main class:touch-mode={useTouchLayout} class:long-rect-mode={activePane === 'rectangle' && isLongRectangleBoard}>
  {#if statusFlight}
    <div
      class="status-flight"
      class:active={statusFlight.active}
      style={`left:${statusFlight.x}px;top:${statusFlight.y}px;--dx:${statusFlight.dx}px;--dy:${statusFlight.dy}px;`}
    >
      {statusFlight.text}
    </div>
  {/if}

  {#if !useTouchLayout}
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

  <nav class="pane pane-tabs" bind:this={paneTabsEl}>
    <button
      class="tab-btn"
      class:active={activePane === 'rectangle'}
      on:click={() => {
        activePane = 'rectangle';
        touchViewMode = 'solver';
      }}
    >
      Rectangle Solver
    </button>
    <button
      class="tab-btn"
      class:active={activePane === 'triplication'}
      on:click={() => {
        activePane = 'triplication';
        touchViewMode = 'solver';
      }}
    >
      Triplication Solver
    </button>
    {#if useTouchLayout}
      <button
        bind:this={solvedToggleEl}
        class="tab-btn touch-solved-toggle"
        class:active={touchViewMode === 'solved'}
        on:click={toggleTouchViewMode}
      >
        Solver / Solved #{activeSolvedCount}
      </button>
    {/if}
  </nav>

  {#if activePane === 'rectangle'}
  {#if !useTouchLayout || touchViewMode === 'solver'}
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
        <p bind:this={rectangleStatusEl} class:error-status={isErrorStatus}>{status}</p>
        <button
          class="status-action"
          class:status-action-hidden={!showResetPrefixAction}
          on:click={onResetStatusActionClick}
          disabled={!showResetPrefixAction}
          aria-hidden={!showResetPrefixAction}
          tabindex={showResetPrefixAction ? 0 : -1}
        >
          Reset to the longest valid prefix
        </button>
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
          on:pointerdown={(event) => startPickerDrag(event, name)}
          disabled={disabled || isRectangleLocked}
          aria-label={`Select ${name}`}
        >
          {#if !useTouchLayout}
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
      <button class="solve" on:click={solveNow} disabled={isRectangleLocked}>Solve</button>
      <button class="solve" on:click={animateSolve} disabled={rectangleSolvedTransitioning}>
        {isAnimating ? 'Stop Animation' : 'Animate Solve'}
      </button>
      {#if !useTouchLayout}
        <span class="pose-readout">steps used: {animationStepsUsed}</span>
        <span class="pose-readout selected-pose-readout">
          {#if selectedPiece}
            {selectedPiece} • rot {pose.rotation * 90}° • {pose.flipped ? 'flipped' : 'normal'}
          {:else}
            all pieces used
          {/if}
        </span>
      {/if}
      {#if useTouchLayout}
        <div class="touch-selected-row">
          <span class="pose-readout touch-selected-readout">
            selected:
            {#if selectedPiece}
              {selectedPiece} • r{pose.rotation * 90} • {pose.flipped ? 'f' : 'n'}
            {:else}
              none
            {/if}
          </span>
          <span class="touch-selected-shape">
            <span
              class="touch-selected-drag-proxy"
              on:pointerdown={(event) => selectedPiece && startPickerDrag(event, selectedPiece)}
            >
            {#if selectedPiece && transformed}
              {@const touchDims = bounds(transformed)}
              <span
                class="mini touch-selected-mini"
                style={`--rows:${touchDims.rows};--cols:${touchDims.cols};--c:${PIECE_COLORS[selectedPiece]}`}
                aria-hidden="true"
              >
                {#each transformed as [r, c]}
                  <span class="cell" style={`grid-row:${r + 1};grid-column:${c + 1}`}></span>
                {/each}
              </span>
            {:else}
              <span class="touch-selected-placeholder" aria-hidden="true"></span>
            {/if}
            </span>
          </span>
        </div>
        <span class="pose-readout">tap: select piece, tap board: place/remove</span>
      {:else}
        <span class="pose-readout">
          keys: piece letter to select, R/Shift+R rotate, X flip, Esc clear ghost
        </span>
      {/if}
      {#if !useTouchLayout && selectedPiece}
        {@const previewCells = transformed && transformed.length > 0 ? transformed : pieceCells(selectedPiece)}
        {@const dims = bounds(previewCells)}
        <span class="active-preview-shell" aria-label="Active transformed preview">
          <span
            class="mini active-preview-mini"
            style={`--rows:${dims.rows};--cols:${dims.cols};--c:${PIECE_COLORS[selectedPiece]}`}
          >
            {#each previewCells as [r, c]}
              <span class="cell" style={`grid-row:${r + 1};grid-column:${c + 1}`}></span>
            {/each}
          </span>
        </span>
      {/if}
    </div>

    <div
      class="board-wrap"
      class:solved-transition={rectangleSolvedTransitioning}
      bind:this={rectangleBoardWrapEl}
      style={`--board-ratio:${rectangleDisplayCols / rectangleDisplayRows};${rectangleSolvedTransitionStyle}`}
    >
      <BoardWebGL
        rows={rectangleDisplayRows}
        cols={rectangleDisplayCols}
        placements={toDisplayPlacements(rectangleRenderPlacements, boardRows, rectangleBoardRotatedView)}
        settleOutlineCells={rectangleSettleOutline}
        floatingPlacement={!rectanglePickerDragActive &&
        rectangleFloatingPlacement &&
        !(rectangleDragInFlight &&
          rectangleDraggedOriginPlacement &&
          !rectangleDraggedPlacementValid)
          ? {
              name: rectangleFloatingPlacement.name,
              cells: rectangleFloatingPlacement.cells.map(([r, c]) =>
                toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
              ),
            }
          : null}
        ghost={!rectanglePickerDragActive &&
        rectangleDragInFlight &&
        rectangleDraggedOriginPlacement &&
        rectangleFloatingPlacement &&
        !rectangleDraggedPlacementValid
          ? {
              name: rectangleFloatingPlacement.name,
              cells: rectangleFloatingPlacement.cells.map(([r, c]) =>
                toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
              ),
              valid: false,
            }
          : ghostPlacement && !ghostOverlapsPlacement
            ? {
                name: ghostPlacement.name,
                cells: ghostPlacement.cells.map(([r, c]) =>
                  toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
                ),
                valid: ghostValid,
              }
            : null}
        interactive={!isRectangleLocked}
          on:cellhover={onBoardHover}
          on:cellclick={onBoardClick}
          on:celldrop={onBoardDrop}
          on:dragstate={onRectangleDragState}
          on:pointermove={onRectanglePointerMove}
        />
    </div>
    {#if rectangleTouchOverlayActive}
      {#if rectanglePickerDragActive}
        <div
          class="touch-board-overlay touch-board-overlay-picker"
          style={rectangleTouchOverlayStyle}
          bind:this={rectangleTouchOverlayEl}
        >
          <BoardWebGL
            rows={rectangleDisplayRows}
            cols={rectangleDisplayCols}
            placements={[]}
            settleOutlineCells={[]}
            floatingPlacement={null}
            ghost={rectangleFloatingPlacement
              ? {
                  name: rectangleFloatingPlacement.name,
                  cells: rectangleFloatingPlacement.cells.map(([r, c]) =>
                    toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
                  ),
                  valid: rectangleDraggedPlacementValid,
                }
              : null}
            interactive={false}
          />
        </div>
      {:else}
        <div class="touch-board-overlay" style={rectangleTouchOverlayStyle}>
          <BoardWebGL
            rows={rectangleDisplayRows}
            cols={rectangleDisplayCols}
            placements={toDisplayPlacements(
              rectangleRenderPlacements,
              boardRows,
              rectangleBoardRotatedView,
            )}
            settleOutlineCells={rectangleSettleOutline}
            floatingPlacement={rectangleFloatingPlacement &&
            !(rectangleDragInFlight &&
              rectangleDraggedOriginPlacement &&
              !rectangleDraggedPlacementValid)
              ? {
                  name: rectangleFloatingPlacement.name,
                  cells: rectangleFloatingPlacement.cells.map(([r, c]) =>
                    toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
                  ),
                }
              : null}
            ghost={rectangleDragInFlight &&
            rectangleDraggedOriginPlacement &&
            rectangleFloatingPlacement &&
            !rectangleDraggedPlacementValid
              ? {
                  name: rectangleFloatingPlacement.name,
                  cells: rectangleFloatingPlacement.cells.map(([r, c]) =>
                    toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
                  ),
                  valid: false,
                }
              : ghostPlacement && !ghostOverlapsPlacement
                ? {
                    name: ghostPlacement.name,
                    cells: ghostPlacement.cells.map(([r, c]) =>
                      toDisplayCell(r, c, boardRows, rectangleBoardRotatedView),
                    ),
                    valid: ghostValid,
                  }
                : null}
            interactive={false}
          />
        </div>
      {/if}
    {/if}

    <div class="slider-row">
      <label for="fixed">Already placed: {prefixCount}</label>
      <input
        id="fixed"
        type="range"
        min="0"
        max={placements.length}
        value={prefixCount}
        disabled={isRectangleLocked}
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
        disabled={isRectangleLocked}
        on:input={onInitialSpeedInput}
      />
      <span>linear slider, exponential speed mapping</span>
    </div>
  </section>
  {/if}

  {#if !useTouchLayout || touchViewMode === 'solved'}
  <aside class="pane solved-pane">
    <header>
      <h2>Solved</h2>
      <p>{useTouchLayout ? 'Tap any solved rectangle to copy it into Solver.' : 'Click any solved rectangle to copy it into Solver.'}</p>
    </header>

    {#if solvedSolutions.length === 0}
      <div class="empty">No solved rectangles yet.</div>
    {:else}
      <div class="solved-list">
        {#each solvedSolutions as solution, idx}
          {@const rotatedSolutionView = solution.cols / solution.rows >= 5}
          <button class="solved-card" on:click={() => importSolved(idx)} disabled={isRectangleLocked}>
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
  {/if}
  {:else}
  {#if !useTouchLayout || touchViewMode === 'solver'}
  <section class="pane triplication-solver-pane">
    <header>
      <div class="solver-title-row">
        <h2>Triplication Solver</h2>
        <button class="solve" on:click={newTriplicationProblem} disabled={isGeneratingTriplication}>
          New Triplication Problem
        </button>
      </div>
      <p bind:this={tripStatusEl} class:error-status={isTripErrorStatus}>{triplicationStatus}</p>
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
            disabled={disabled || isTriplicationLocked}
            aria-label={`Select ${name}`}
          >
            {#if !useTouchLayout}
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
        <button class="solve" on:click={solveTriplicationNow} disabled={isTriplicationLocked}>Solve</button>
        <button class="solve" on:click={animateTriplicationSolve}>
          {tripIsAnimating ? 'Stop Animation' : 'Animate Solve'}
        </button>
        {#if !useTouchLayout}
          <span class="pose-readout">steps used: {tripAnimationStepsUsed}</span>
          <span class="pose-readout selected-pose-readout">
            {#if tripSelectedPiece}
              {tripSelectedPiece} • rot {tripPose.rotation * 90}° • {tripPose.flipped ? 'flipped' : 'normal'}
            {:else}
              all selected pieces used
            {/if}
          </span>
        {/if}
        {#if useTouchLayout}
          <div class="touch-selected-row">
            <span class="pose-readout touch-selected-readout">
              selected:
              {#if tripSelectedPiece}
                {tripSelectedPiece} • r{tripPose.rotation * 90} •
                {tripPose.flipped ? 'f' : 'n'}
              {:else}
                none
              {/if}
            </span>
            <span class="touch-selected-shape">
              {#if tripSelectedPiece && tripTransformed}
                {@const touchTripDims = bounds(tripTransformed)}
                <span
                  class="mini touch-selected-mini"
                  style={`--rows:${touchTripDims.rows};--cols:${touchTripDims.cols};--c:${PIECE_COLORS[tripSelectedPiece]}`}
                  aria-hidden="true"
                >
                  {#each tripTransformed as [r, c]}
                    <span class="cell" style={`grid-row:${r + 1};grid-column:${c + 1}`}></span>
                  {/each}
                </span>
              {:else}
                <span class="touch-selected-placeholder" aria-hidden="true"></span>
              {/if}
            </span>
          </div>
          <span class="pose-readout">tap: select piece, tap board: place/remove</span>
        {:else}
          <span class="pose-readout">
            keys: piece letter to select, R/Shift+R rotate, X flip, Esc clear ghost
          </span>
        {/if}
        {#if !useTouchLayout && tripSelectedPiece}
          {@const previewCells = tripTransformed && tripTransformed.length > 0 ? tripTransformed : pieceCells(tripSelectedPiece)}
          {@const dims = bounds(previewCells)}
          <span class="active-preview-shell" aria-label="Active transformed preview">
            <span
              class="mini active-preview-mini"
              style={`--rows:${dims.rows};--cols:${dims.cols};--c:${PIECE_COLORS[tripSelectedPiece]}`}
            >
              {#each previewCells as [r, c]}
                <span class="cell" style={`grid-row:${r + 1};grid-column:${c + 1}`}></span>
              {/each}
            </span>
          </span>
        {/if}
      </div>

      <div
        class="board-wrap"
        class:solved-transition={tripSolvedTransitioning}
        bind:this={tripBoardWrapEl}
        style={`--board-ratio:${triplicationProblem.cols / triplicationProblem.rows};${tripSolvedTransitionStyle}`}
      >
        <BoardWebGL
          rows={triplicationProblem.rows}
          cols={triplicationProblem.cols}
          placements={tripRenderPlacements}
          settleOutlineCells={tripSettleOutline}
          floatingPlacement={null}
          maskCells={triplicationProblem.maskCells}
          ghost={null}
          interactive={!isTriplicationLocked}
          on:cellhover={onTripBoardHover}
          on:cellclick={onTripBoardClick}
          on:celldrop={onTripBoardDrop}
          on:dragstate={onTripDragState}
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
          disabled={isTriplicationLocked}
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
          disabled={isTriplicationLocked}
          on:input={onTripInitialSpeedInput}
        />
        <span>linear slider, exponential speed mapping</span>
      </div>
    {/if}
  </section>
  {/if}

  {#if !useTouchLayout || touchViewMode === 'solved'}
  <aside class="pane solved-pane trip-solved-pane">
    <header>
      <h2>Solved</h2>
      <p>
        {useTouchLayout
          ? 'Tap any solved triplication to copy it into Triplication Solver.'
          : 'Click any solved triplication to copy it into Triplication Solver.'}
      </p>
    </header>

    {#if tripSolvedSolutions.length === 0}
      <div class="empty">No solved triplication boards yet.</div>
    {:else}
      <div class="solved-list">
        {#each tripSolvedSolutions as solution, idx}
          <button class="solved-card" on:click={() => importTripSolved(idx)} disabled={isTriplicationLocked}>
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
  {/if}
</main>
