import { test, expect } from '@playwright/test';

// Use the Vite preview server base URL if available, otherwise fallback to localhost:5173
const BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:5173';

// Basic smoke test for the main page

test('homepage loads and displays Route Visualizer', async ({ page }) => {
  await page.goto(BASE_URL + '/');
  await expect(page.getByRole('heading', { name: /Route Visualizer/i })).toBeVisible();
});

test('routes table is visible', async ({ page }) => {
  await page.goto(BASE_URL + '/');
  await expect(page.getByRole('table')).toBeVisible();
});
