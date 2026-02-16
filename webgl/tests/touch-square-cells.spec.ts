import { expect, test } from '@playwright/test';

test('touch mode keeps board cells square', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'touch', 'This test runs in touch project only.');

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();

  const boardWrap = page.locator('section.solver-pane .board-wrap').first();
  await expect(boardWrap).toBeVisible();

  const canvas = page.locator('section.solver-pane .board-wrap canvas').first();
  await expect(canvas).toBeVisible();
  await canvas.scrollIntoViewIfNeeded();

  const boardRatio = await boardWrap.evaluate((el) => {
    const value = getComputedStyle(el).getPropertyValue('--board-ratio').trim();
    return Number(value);
  });
  expect(Number.isFinite(boardRatio)).toBeTruthy();

  const box = await canvas.boundingBox();
  if (!box) {
    throw new Error('Board canvas has no bounding box');
  }

  const renderedRatio = box.width / box.height;
  expect(Math.abs(renderedRatio - boardRatio)).toBeLessThan(0.03);
});
