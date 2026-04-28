import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test('home page has zero axe violations (WCAG 2.1 AA)', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  // Print violations to make CI failures actionable
  if (results.violations.length > 0) {
    // eslint-disable-next-line no-console
    console.log(JSON.stringify(results.violations, null, 2));
  }

  expect(results.violations).toEqual([]);
});

test('home page has zero axe violations in Hindi', async ({ page }) => {
  await page.goto('/');
  await page
    .getByRole('combobox', { name: /language/i })
    .selectOption('hi');

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();

  if (results.violations.length > 0) {
    // eslint-disable-next-line no-console
    console.log(JSON.stringify(results.violations, null, 2));
  }

  expect(results.violations).toEqual([]);
});
