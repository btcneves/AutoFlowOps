#!/usr/bin/env node
/**
 * Capture screenshots of all AutoFlowOps pages with demo data.
 * Usage: node scripts/capture_screenshots.js
 * Requires: stack running (make up && make seed), Playwright installed
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:3000';
const OUT_DIR = path.join(__dirname, '..', 'docs', 'assets', 'screenshots');
const VIEWPORT = { width: 1440, height: 900 };

const CREDENTIALS = { email: 'admin@autoflowops.local', password: 'changeme' };

async function login(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', CREDENTIALS.email);
  await page.fill('input[type="password"]', CREDENTIALS.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/`, { timeout: 10000 });
}

async function shot(page, name, route, { waitFor, extraDelay = 400 } = {}) {
  console.log(`  -> ${name} (${route})`);
  await page.goto(`${BASE_URL}${route}`, { waitUntil: 'networkidle' });
  if (waitFor) await page.waitForSelector(waitFor, { timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(extraDelay);
  await page.screenshot({ path: path.join(OUT_DIR, `${name}.png`), fullPage: false });
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  // --- Login page (unauthenticated) ---
  console.log('[1/16] Login page');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(OUT_DIR, 'login.png') });

  // --- Authenticate ---
  console.log('[2/16] Authenticating...');
  await page.fill('input[type="email"]', CREDENTIALS.email);
  await page.fill('input[type="password"]', CREDENTIALS.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/`, { timeout: 10000 });

  // --- Dashboard ---
  console.log('[3/16] Dashboard');
  await shot(page, 'dashboard', '/', { waitFor: '[class*="recharts"]', extraDelay: 800 });

  // --- Jobs list ---
  console.log('[4/16] Jobs list');
  await shot(page, 'jobs', '/jobs', { waitFor: 'table', extraDelay: 500 });

  // --- Job detail (first job) ---
  console.log('[5/16] Job detail');
  await page.goto(`${BASE_URL}/jobs`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  const jobLink = page.locator('table tbody tr a, table tbody tr [role="link"], table tbody tr td:first-child').first();
  const clicked = await jobLink.click({ timeout: 5000 }).then(() => true).catch(() => false);
  if (clicked) {
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, 'job-detail.png') });
  } else {
    // fallback: try /jobs/1
    await shot(page, 'job-detail', '/jobs/1', { extraDelay: 500 });
  }

  // --- Job form (create) ---
  console.log('[6/16] Job form (create)');
  await shot(page, 'job-form', '/jobs/new', { waitFor: 'form', extraDelay: 500 });

  // --- Executions list ---
  console.log('[7/16] Executions');
  await shot(page, 'executions', '/executions', { waitFor: 'table', extraDelay: 500 });

  // --- Execution detail (first) ---
  console.log('[8/16] Execution detail');
  await page.goto(`${BASE_URL}/executions`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  const execLink = page.locator('table tbody tr').first();
  const execClicked = await execLink.click({ timeout: 5000 }).then(() => true).catch(() => false);
  if (execClicked) {
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT_DIR, 'execution-detail.png') });
  } else {
    await shot(page, 'execution-detail', '/executions/1', { extraDelay: 500 });
  }

  // --- Alerts ---
  console.log('[9/16] Alerts');
  await shot(page, 'alerts', '/alerts', { waitFor: 'table', extraDelay: 500 });

  // --- Webhooks ---
  console.log('[10/16] Webhooks');
  await shot(page, 'webhooks', '/webhooks', { waitFor: 'table', extraDelay: 500 });

  // --- Notification Channels ---
  console.log('[11/16] Notification Channels');
  await shot(page, 'notification-channels', '/notification-channels', { extraDelay: 500 });

  // --- Notification Templates ---
  console.log('[12/16] Notification Templates');
  await shot(page, 'notification-templates', '/notification-templates', { extraDelay: 500 });

  // --- Escalation Policies ---
  console.log('[13/16] Escalation Policies');
  await shot(page, 'escalation-policies', '/escalation-policies', { extraDelay: 500 });

  // --- Reports ---
  console.log('[14/16] Reports');
  await shot(page, 'reports', '/reports', { waitFor: 'table', extraDelay: 500 });

  // --- Users ---
  console.log('[15/16] Users');
  await shot(page, 'users', '/users', { waitFor: 'table', extraDelay: 500 });

  // --- Audit Logs ---
  console.log('[16/16] Audit Logs');
  await shot(page, 'audit-logs', '/audit-logs', { waitFor: 'table', extraDelay: 600 });

  await browser.close();

  const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.png'));
  console.log(`\nDone. ${files.length} screenshots in docs/assets/screenshots/:`);
  files.forEach(f => {
    const size = fs.statSync(path.join(OUT_DIR, f)).size;
    console.log(`  ${f.padEnd(35)} ${(size / 1024).toFixed(0)} KB`);
  });
})();
