import { expect, test, type Page } from '@playwright/test';
import { PIECES } from '../src/lib/pentomino';

const BOARD_ROWS = 5;
const BOARD_COLS = 12;
const UI_STATE_STORAGE_KEY = 'pentomanim:webgl:ui-state:v1';

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

async function pointForBoardWrapCell(
  page: Page,
  row: number,
  col: number,
): Promise<{ x: number; y: number }> {
  const wrap = page.locator('section.solver-pane .board-wrap').first();
  await expect(wrap).toBeVisible();
  await wrap.scrollIntoViewIfNeeded();
  const box = await wrap.boundingBox();
  if (!box) {
    throw new Error('Board wrap has no bounding box');
  }
  return {
    x: box.x + ((col + 0.5) * box.width) / BOARD_COLS,
    y: box.y + ((row + 0.5) * box.height) / BOARD_ROWS,
  };
}

async function dragFromPickerToBoardMouse(
  page: Page,
  piece: string,
  toCell: [number, number],
): Promise<void> {
  const picker = page.getByRole('button', { name: `Select ${piece}` }).first();
  await expect(picker).toBeVisible();
  const pickerBox = await picker.boundingBox();
  if (!pickerBox) {
    throw new Error('Picker button has no bounding box');
  }
  const from = {
    x: pickerBox.x + pickerBox.width / 2,
    y: pickerBox.y + pickerBox.height / 2,
  };
  const to = await pointForBoardWrapCell(page, toCell[0], toCell[1]);
  await picker.dispatchEvent('pointerdown', {
    pointerId: 44,
    pointerType: 'mouse',
    button: 0,
    buttons: 1,
    clientX: from.x,
    clientY: from.y,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });
  await page.evaluate(
    ({ x, y }) => {
      window.dispatchEvent(
        new PointerEvent('pointermove', {
          pointerId: 44,
          pointerType: 'mouse',
          button: 0,
          buttons: 1,
          clientX: x,
          clientY: y,
          bubbles: true,
          composed: true,
          isPrimary: true,
        }),
      );
    },
    { x: to.x, y: to.y },
  );
  await page.evaluate(
    ({ x, y }) => {
      window.dispatchEvent(
        new PointerEvent('pointerup', {
          pointerId: 44,
          pointerType: 'mouse',
          button: 0,
          buttons: 0,
          clientX: x,
          clientY: y,
          bubbles: true,
          composed: true,
          isPrimary: true,
        }),
      );
    },
    { x: to.x, y: to.y },
  );
}

async function dragFromPickerToBoardTouch(
  page: Page,
  piece: string,
  toCell: [number, number],
): Promise<void> {
  const picker = page.getByRole('button', { name: `Select ${piece}` }).first();
  await expect(picker).toBeVisible();
  const pickerBox = await picker.boundingBox();
  if (!pickerBox) {
    throw new Error('Picker button has no bounding box');
  }
  const from = {
    x: pickerBox.x + pickerBox.width / 2,
    y: pickerBox.y + pickerBox.height / 2,
  };
  const to = await pointForBoardWrapCell(page, toCell[0], toCell[1]);
  await picker.dispatchEvent('pointerdown', {
    pointerId: 33,
    pointerType: 'touch',
    button: 0,
    buttons: 1,
    clientX: from.x,
    clientY: from.y,
    bubbles: true,
    composed: true,
    isPrimary: true,
  });
  await page.evaluate(
    ({ x, y }) => {
      window.dispatchEvent(
        new PointerEvent('pointermove', {
          pointerId: 33,
          pointerType: 'touch',
          button: 0,
          buttons: 1,
          clientX: x,
          clientY: y,
          bubbles: true,
          composed: true,
          isPrimary: true,
        }),
      );
    },
    { x: to.x, y: to.y },
  );
  await page.evaluate(
    ({ x, y }) => {
      window.dispatchEvent(
        new PointerEvent('pointerup', {
          pointerId: 33,
          pointerType: 'touch',
          button: 0,
          buttons: 0,
          clientX: x,
          clientY: y,
          bubbles: true,
          composed: true,
          isPrimary: true,
        }),
      );
    },
    { x: to.x, y: to.y },
  );
}

async function expectPlacedCountOrStatus(page: Page, count: string): Promise<void> {
  if ((await page.locator('input#fixed').count()) > 0) {
    await expect(page.locator('input#fixed')).toHaveValue(count);
    return;
  }
  await expect(page.locator('header .status-row p')).toContainText('placed');
}

test('persists mode, rectangle size, placements, and solved list across reload', async ({
  page,
}, testInfo) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();
  await page.locator('label.board-size-select select').selectOption('12x5');

  const anchor: [number, number] = [1, 1];
  const dropCell = clickCellForAnchor(anchor, PIECES.F);
  if (testInfo.project.name === 'touch') {
    await dragFromPickerToBoardTouch(page, 'F', [dropCell[0], dropCell[1]]);
  } else {
    await dragFromPickerToBoardMouse(page, 'F', [dropCell[0], dropCell[1]]);
  }
  await expectPlacedCountOrStatus(page, '1');

  await page.getByRole('button', { name: 'Triplication Solver' }).click();
  await expect(
    page.getByRole('button', { name: 'Triplication Solver' }),
  ).toHaveClass(/active/);

  await page.evaluate((key) => {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      throw new Error('Missing persisted UI state');
    }
    const state = JSON.parse(raw);
    state.solvedSolutions = [
      {
        rows: 5,
        cols: 12,
        placements: [{ name: 'F', cells: [[0, 1], [1, 0], [1, 1], [1, 2], [2, 0]] }],
      },
    ];
    window.localStorage.setItem(key, JSON.stringify(state));
  }, UI_STATE_STORAGE_KEY);

  await page.reload();
  await expect(
    page.getByRole('button', { name: 'Triplication Solver' }),
  ).toHaveClass(/active/);

  await page.getByRole('button', { name: 'Rectangle Solver' }).click();
  await expect(page.locator('label.board-size-select select')).toHaveValue('12x5');
  await expectPlacedCountOrStatus(page, '1');
  if (testInfo.project.name === 'touch') {
    await page.getByRole('button', { name: /Solver \/ Solved/ }).click();
  }
  await expect(page.locator('.solved-card .solved-index').first()).toContainText(
    'Rectangle 1',
  );
});
