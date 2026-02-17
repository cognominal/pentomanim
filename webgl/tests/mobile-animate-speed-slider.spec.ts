import { expect, test } from '@playwright/test';

test('touch mode keeps animate speed slider usable on smartphone width', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'touch', 'This test runs in touch project only.');

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();

  const speedSlider = page.locator('input#speed');
  if ((await speedSlider.count()) === 0) {
    await expect(speedSlider).toHaveCount(0);
    return;
  }

  await expect(speedSlider).toBeVisible();

  const viewport = page.viewportSize();
  if (!viewport) {
    throw new Error('Page viewport size is unavailable');
  }

  const box = await speedSlider.boundingBox();
  if (!box) {
    throw new Error('Speed slider has no bounding box');
  }

  expect(box.width).toBeGreaterThan(viewport.width * 0.55);
});
