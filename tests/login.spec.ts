import { test, expect } from '@playwright/test';
import { LoginPage } from '../page-objects/LoginPage';

test('Login to CRM', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login(process.env.CRM_EMAIL!, process.env.CRM_PASSWORD!);
  await expect(page).toHaveURL(/dashboard/i);
});