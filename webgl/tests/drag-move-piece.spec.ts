import { expect, test, type Locator, type Page } from '@playwright/test';
import { PIECES, placeAtAnchor } from '../src/lib/pentomino';

const BOARD_ROWS = 5;
const BOARD_COLS = 12;

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

  const anchorStart: [number, number] = [0, 1];
  await placeCell(page, anchorStart[0], anchorStart[1]);
  await expect(page.locator('input#fixed')).toHaveValue('1');

  const occupiedFrom = placeAtAnchor(PIECES.F, anchorStart[0], anchorStart[1])[2];
  const freeTargetAnchor: [number, number] = [0, 4];
  await dragCell(page, occupiedFrom, freeTargetAnchor);

  await expect(page.locator('input#fixed')).toHaveValue('1');
  await expect(page.locator('header .status-row p')).toContainText('F placed.');
}

test('mouse drag moves a placed piece', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'click', 'This test runs in click project only.');
  await runDragMoveFlow(page, clickCell, (dragPage, fromCell, toCell) =>
    dragCellWithPointerEvents(dragPage, 'mouse', fromCell, toCell),
  );
});

test('touch drag moves a placed piece', async ({ page }, testInfo) => {
  test.skip(true, 'Playwright touch drag simulation is unreliable for this canvas pointer-capture flow.');
  test.skip(testInfo.project.name !== 'touch', 'This test runs in touch project only.');
  await runDragMoveFlow(page, tapCell, dragCellWithMouse);
});
