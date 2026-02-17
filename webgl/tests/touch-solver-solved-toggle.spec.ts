import { expect, test, type Page } from '@playwright/test';

async function expectNoPageScroll(page: Page): Promise<void> {
  const metrics = await page.evaluate(() => {
    const root = document.scrollingElement ?? document.documentElement;
    return {
      scrollHeight: root.scrollHeight,
      scrollWidth: root.scrollWidth,
      innerHeight: window.innerHeight,
      innerWidth: window.innerWidth,
    };
  });

  expect(metrics.scrollHeight).toBeLessThanOrEqual(metrics.innerHeight + 1);
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.innerWidth + 1);
}

test('touch mode toggles between Solver/Solved and auto-switches after solve without page scrolling', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== 'touch', 'This test runs in touch project only.');

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Rectangle Solver' })).toBeVisible();

  const toggle = page.locator('button.touch-solved-toggle');
  await expect(toggle).toHaveText('Solver / Solved #0');
  await expect(page.locator('section.solver-pane')).toBeVisible();
  await expect(page.locator('aside.solved-pane')).toHaveCount(0);
  await expectNoPageScroll(page);

  await page.locator('section.solver-pane button.solve', { hasText: /^Solve$/ }).click();
  await expect(toggle).toHaveText('Solver / Solved #1', { timeout: 10000 });

  await expect(page.locator('aside.solved-pane')).toBeVisible({ timeout: 10000 });
  await expect(page.locator('section.solver-pane')).toHaveCount(0);
  await expectNoPageScroll(page);

  await toggle.click();
  await expect(page.locator('section.solver-pane')).toBeVisible();
  await expect(page.locator('aside.solved-pane')).toHaveCount(0);
  await expectNoPageScroll(page);
});
