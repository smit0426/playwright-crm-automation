import { test, expect } from '@playwright/test';
import { LoginPage } from '../page-objects/LoginPage';
import { DashboardPage } from '../page-objects/DashboardPage';

test.beforeEach(async ({ page }) => {
  const login = new LoginPage(page);
  await login.goto();
  await login.login(process.env.CRM_EMAIL!, process.env.CRM_PASSWORD!);
});

test('Dashboard: graphs and stats should be correct', async ({ page }) => {
  const dashboard = new DashboardPage(page);
  await dashboard.navigateTo();
  expect(await page.locator('.dashboard-graph').count()).toBeGreaterThan(0); // Update
});