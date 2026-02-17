import { expect, test, type Locator, type Page } from '@playwright/test';
import { PIECES, placeAtAnchor } from '../src/lib/pentomino';

const BOARD_ROWS = 5;
const BOARD_COLS = 12;

function pieceBarycenter(cells: [number, number][]): { row: number; col: number } {
  const count = cells.length || 1;
  const row = cells.reduce((sum, [r]) => sum + r + 0.5, 0) / count;
  const col = cells.reduce((sum, [, c]) => sum + c + 0.5, 0) / count;
  return { row, col };
}

function clickCellForAnchor(
  anchor: [number, number],
  cells: [number, number][],
): [number, number] {
  const center = pieceBarycenter(cells);
  return [
    Math.round(anchor[0] + center.row - 0.5),
    Math.round(anchor[1] + center.col - 0.5),
  ];
}

async function boardCanvas(page: Page): Promise<Locator> {
  const canvas = page.locator('section.solver-pane .board-wrap canvas').first();
  await expect(canvas).toBeVisible();
  await canvas.scrollIntoViewIfNeeded();
  return canvas;
}

async function pointForCell(page: Page, row: number, col: number): Promise<{ x: number; y: number }> {
  const canvas = await boardCanvas(page);
  const box = await canvas.boundingBox();
  if (!box) {
    throw new Error('Board canvas has no bounding box');
  }
  return {
    x: box.x + ((col + 0.5) * box.width) / BOARD_COLS,
    y: box.y + ((row + 0.5) * box.height) / BOARD_ROWS,
  };
}

async function clickCell(page: Page, row: number, col: number): Promise<void> {
  const point = await pointForCell(page, row, col);
  await page.mouse.click(point.x, point.y);
}

async function tapCell(page: Page, row: number, col: number): Promise<void> {
  const point = await pointForCell(page, row, col);
  await page.touchscreen.tap(point.x, point.y);
}

async function dragCellWithPointerEvents(
  page: Page,
  pointerType: 'mouse' | 'touch',
  fromCell: [number, number],
  toCell: [number, number],
): Promise<void> {
  const canvas = await boardCanvas(page);
  const from = await pointForCell(page, fromCell[0], fromCell[1]);
  const to = await pointForCell(page, toCell[0], toCell[1]);
  const pointerId = pointerType === 'touch' ? 11 : 1;

  await canvas.dispatchEvent('pointerdown', {
    pointerId,
    pointerType,
    button: 0,
    buttons: 1,
    clientX: from.x,
    clientY: from.y,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });
  await canvas.dispatchEvent('pointermove', {
    pointerId,
    pointerType,
    button: 0,
    buttons: 1,
    clientX: to.x,
    clientY: to.y,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });
  await canvas.dispatchEvent('pointerup', {
    pointerId,
    pointerType,
    button: 0,
    buttons: 0,
    clientX: to.x,
    clientY: to.y,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });
}

async function dragCellWithMouse(
  page: Page,
  fromCell: [number, number],
  toCell: [number, number],
): Promise<void> {
  const from = await pointForCell(page, fromCell[0], fromCell[1]);
  const to = await pointForCell(page, toCell[0], toCell[1]);
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(to.x, to.y);
  await page.mouse.up();
}

async function runDragMoveFlow(
  page: Page,
  placeCell: (page: Page, row: number, col: number) => Promise<void>,
  dragCell: (page: Page, fromCell: [number, number], toCell: [number, number]) => Promise<void>,
) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();
  await page.locator('label.board-size-select select').selectOption('12x5');

  const anchorStart: [number, number] = [1, 1];
  const placeStartCell = clickCellForAnchor(anchorStart, PIECES.F);
  await placeCell(page, placeStartCell[0], placeStartCell[1]);
  if ((await page.locator('input#fixed').count()) > 0) {
    await expect(page.locator('input#fixed')).toHaveValue('1');
  } else {
    await expect(page.locator('header .status-row p')).toContainText('F placed.');
  }

  const occupiedFrom = placeAtAnchor(PIECES.F, anchorStart[0], anchorStart[1])[2];
  const freeTargetAnchor: [number, number] = [1, 4];
  const targetCell = clickCellForAnchor(freeTargetAnchor, PIECES.F);
  await dragCell(page, occupiedFrom, targetCell);

  if ((await page.locator('input#fixed').count()) > 0) {
    await expect(page.locator('input#fixed')).toHaveValue('1');
  }
  await expect(page.locator('header .status-row p')).toContainText('F placed.');
}

test('mouse drag moves a placed piece', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'click', 'This test runs in click project only.');
  await runDragMoveFlow(page, clickCell, dragCellWithMouse);
});

test('touch drag moves a placed piece', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'touch', 'This test runs in touch project only.');
  await runDragMoveFlow(
    page,
    tapCell,
    (p, from, to) => dragCellWithPointerEvents(p, 'touch', from, to),
  );
});

test('click on placed piece removes it without drag', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'click', 'This test runs in click project only.');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();
  await page.locator('label.board-size-select select').selectOption('12x5');

  const anchorStart: [number, number] = [1, 1];
  const placeStartCell = clickCellForAnchor(anchorStart, PIECES.F);
  await clickCell(page, placeStartCell[0], placeStartCell[1]);
  await expect(page.locator('input#fixed')).toHaveValue('1');

  const occupiedCell = placeAtAnchor(PIECES.F, anchorStart[0], anchorStart[1])[2];
  await clickCell(page, occupiedCell[0], occupiedCell[1]);

  await expect(page.locator('input#fixed')).toHaveValue('0');
});

test('barycenter pickup has no initial right jump', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'click', 'This test runs in click project only.');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();
  await page.locator('label.board-size-select select').selectOption('12x5');

  const anchorStart: [number, number] = [1, 1];
  const placeStartCell = clickCellForAnchor(anchorStart, PIECES.F);
  await clickCell(page, placeStartCell[0], placeStartCell[1]);
  await expect(page.locator('input#fixed')).toHaveValue('1');

  const pickCell = placeAtAnchor(PIECES.F, anchorStart[0], anchorStart[1])[2];
  const start = await pointForCell(page, pickCell[0], pickCell[1]);
  const canvas = await boardCanvas(page);

  await page.evaluate(() => {
    (window as unknown as { __dragSamples: unknown[] }).__dragSamples = [];
    window.addEventListener(
      'pento:drag-sample',
      ((event: Event) => {
        const custom = event as CustomEvent<{
          deltaRow: number;
          deltaCol: number;
          snapDeltaRow: number;
          snapDeltaCol: number;
        }>;
        const store = window as unknown as {
          __dragSamples: Array<{
            deltaRow: number;
            deltaCol: number;
            snapDeltaRow: number;
            snapDeltaCol: number;
          }>;
        };
        store.__dragSamples.push(custom.detail);
      }) as EventListener,
      { once: false },
    );
  });

  const moveDxPx = 2;
  const moveDyPx = 0;

  await canvas.dispatchEvent('pointerdown', {
    pointerId: 1,
    pointerType: 'mouse',
    button: 0,
    buttons: 1,
    clientX: start.x,
    clientY: start.y,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });
  await canvas.dispatchEvent('pointermove', {
    pointerId: 1,
    pointerType: 'mouse',
    button: 0,
    buttons: 1,
    clientX: start.x + moveDxPx,
    clientY: start.y + moveDyPx,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });

  await page.waitForFunction(() => {
    const store = window as unknown as {
      __dragSamples?: Array<{ deltaCol?: number; deltaRow?: number }>;
    };
    if (!store.__dragSamples || store.__dragSamples.length === 0) {
      return false;
    }
    return store.__dragSamples.some(
      (sample) =>
        Number.isFinite(sample?.deltaCol) && Number.isFinite(sample?.deltaRow),
    );
  });

  const first = await page.evaluate(() => {
    const store = window as unknown as {
      __dragSamples: Array<{
        deltaRow: number;
        deltaCol: number;
        snapDeltaRow: number;
        snapDeltaCol: number;
      }>;
    };
    return (
      store.__dragSamples.find(
        (sample) =>
          Number.isFinite(sample.deltaCol) && Number.isFinite(sample.deltaRow),
      ) ?? null
    );
  });

  expect(first).not.toBeNull();
  if (!first) {
    return;
  }
  expect(Math.abs(first.snapDeltaCol)).toBeLessThan(0.001);
  expect(Math.abs(first.snapDeltaRow)).toBeLessThan(0.001);

  await canvas.dispatchEvent('pointerup', {
    pointerId: 1,
    pointerType: 'mouse',
    button: 0,
    buttons: 0,
    clientX: start.x + moveDxPx,
    clientY: start.y + moveDyPx,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });
});

test('drag release outside board removes dragged piece', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'click', 'This test runs in click project only.');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();
  await page.locator('label.board-size-select select').selectOption('12x5');

  const anchorStart: [number, number] = [1, 1];
  const placeStartCell = clickCellForAnchor(anchorStart, PIECES.F);
  await clickCell(page, placeStartCell[0], placeStartCell[1]);
  await expect(page.locator('input#fixed')).toHaveValue('1');

  const occupiedFrom = placeAtAnchor(PIECES.F, anchorStart[0], anchorStart[1])[2];
  const from = await pointForCell(page, occupiedFrom[0], occupiedFrom[1]);

  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x - 220, from.y);
  await page.mouse.up();

  await expect(page.locator('input#fixed')).toHaveValue('0');
});

test('drag release on occupied area removes dragged piece', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'click', 'This test runs in click project only.');
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();
  await page.locator('label.board-size-select select').selectOption('12x5');

  const anchorF: [number, number] = [1, 1];
  const placeF = clickCellForAnchor(anchorF, PIECES.F);
  await clickCell(page, placeF[0], placeF[1]);
  await expect(page.locator('input#fixed')).toHaveValue('1');

  await page.getByRole('button', { name: 'Select I' }).click();
  const anchorI: [number, number] = [1, 6];
  const placeI = clickCellForAnchor(anchorI, PIECES.I);
  await clickCell(page, placeI[0], placeI[1]);
  await expect(page.locator('input#fixed')).toHaveValue('2');

  const occupiedFrom = placeAtAnchor(PIECES.F, anchorF[0], anchorF[1])[2];
  const occupiedTarget = placeAtAnchor(PIECES.I, anchorI[0], anchorI[1])[2];
  await dragCellWithMouse(page, occupiedFrom, occupiedTarget);

  await expect(page.locator('input#fixed')).toHaveValue('1');
});
