import { test, expect } from '@playwright/test';
import { LoginPage } from '../page-objects/LoginPage';

test('Login and see dashboard', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.goto();
  await loginPage.login('testuser', 'testpassword');
  await expect(page).toHaveTitle(/Dashboard/);
});