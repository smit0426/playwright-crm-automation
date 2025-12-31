# Playwright Guardian CRM Automation

## Setup

```bash
npm install
```

- Copy `.env` and fill with your login details.

## Run Tests

Run all tests:
```bash
npx playwright test
```
Run with browser visible:
```bash
npx playwright test --headed
```
View the HTML report (after running):
```bash
npx playwright show-report
```

## Add/Edit Tests

- Update selectors in `page-objects/` as needed.
- Expand logic in `tests/` files.

## .env Example

```env
CRM_URL=https://guardiancapitalusa.com/login
CRM_EMAIL=pabloescobar@yopmail.com
CRM_PASSWORD=Test@123
```