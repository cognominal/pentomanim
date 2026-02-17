import { expect, test, type Page } from '@playwright/test';

const BOARD_ROWS = 6;
const BOARD_COLS = 10;

async function boardCanvas(page: Page) {
  const canvas = page.locator('section.solver-pane .board-wrap canvas').first();
  await expect(canvas).toBeVisible();
  await canvas.scrollIntoViewIfNeeded();
  return canvas;
}

async function clickCell(page: Page, row: number, col: number): Promise<void> {
  const canvas = await boardCanvas(page);
  const box = await canvas.boundingBox();
  if (!box) {
    throw new Error('Board canvas has no bounding box');
  }
  const x = box.x + ((col + 0.5) * box.width) / BOARD_COLS;
  const y = box.y + ((row + 0.5) * box.height) / BOARD_ROWS;
  await page.mouse.click(x, y);
}

async function tapCell(page: Page, row: number, col: number): Promise<void> {
  const canvas = await boardCanvas(page);
  const box = await canvas.boundingBox();
  if (!box) {
    throw new Error('Board canvas has no bounding box');
  }
  const x = box.x + ((col + 0.5) * box.width) / BOARD_COLS;
  const y = box.y + ((row + 0.5) * box.height) / BOARD_ROWS;
  await page.touchscreen.tap(x, y);
}

async function runInvalidPrefixFlow(
  page: Page,
  placeCell: (p: Page, row: number, col: number) => Promise<void>,
  expectedIntro: string,
  expectPrefixSlider: boolean,
) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();
  await expect(page.locator('header .status-row p')).toContainText(expectedIntro);

  // F is selected by default; place it at anchor (row=0, col=1).
  await placeCell(page, 0, 1);
  await expect(page.locator('header .status-row p')).toContainText('F placed.');

  await page.getByRole('button', { name: 'Select I' }).click();
  // Place horizontal I at row 3, columns 0..4. This prefix has 0 completions.
  await placeCell(page, 3, 0);

  await expect(page.locator('header .status-row p')).toContainText('I placed. 0 solutions for this prefix.');
  await expect(page.getByRole('button', { name: 'Reset to the longest valid prefix' })).toBeVisible();
  if (expectPrefixSlider) {
    await expect(page.locator('input#fixed')).toHaveValue('2');
  } else {
    await expect(page.locator('input#fixed')).toHaveCount(0);
  }

  await page.getByRole('button', { name: 'Reset to the longest valid prefix' }).click();
  await expect(page.locator('header .status-row p')).toContainText('Reset to longest valid prefix (1 pieces).');
  if (expectPrefixSlider) {
    await expect(page.locator('input#fixed')).toHaveValue('1');
  }
}

test('click mode accepts placement then offers reset-to-prefix', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'click', 'This test runs in click project only.');
  await runInvalidPrefixFlow(page, clickCell, 'Pick a piece and click the board to place it.', true);
});

test('touch mode accepts placement then offers reset-to-prefix', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'touch', 'This test runs in touch project only.');
  await runInvalidPrefixFlow(page, tapCell, 'Pick a piece and tap the board to place it.', false);
});
