import { expect, test } from '@playwright/test';

test('home renders the sign-in surface', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Audiobook-Assistant/i, level: 1 })).toBeVisible();
  await expect(page.getByPlaceholder(/you@example\.com/i)).toBeVisible();
});

test('sign-in form rejects empty email', async ({ page }) => {
  await page.goto('/');
  // HTML5 required attribute should block submit
  await page.getByRole('button', { name: /sign in/i }).click();
  // Form did not navigate / change state — still on home
  await expect(page).toHaveURL(/\/$/);
});

test('language switcher toggles the tagline', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('combobox', { name: /language/i }).selectOption('hi');
  await expect(page.getByText(/बहुभाषी/)).toBeVisible();
});

test('skip-to-main link is reachable via keyboard', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Tab');
  // The first tabbable element in our DOM is the skip link
  const focused = page.locator(':focus');
  await expect(focused).toContainText(/skip to main/i);
});
