import { Page } from '@playwright/test';

export class CalendarPage {
  readonly page: Page;
  constructor(page: Page) { this.page = page; }
  async navigateTo() { await this.page.click('nav >> text=Calendar'); await this.page.waitForLoadState('networkidle'); }
  async createItem() {/* Implement */}
  async readItem() {/* Implement */}
  async updateItem() {/* Implement */}
  async deleteItem() {/* Implement */}
}