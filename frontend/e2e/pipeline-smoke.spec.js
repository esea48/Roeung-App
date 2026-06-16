import fs from 'node:fs';
import path from 'node:path';
import { test, expect, chromium } from '@playwright/test';

const familyToken = process.env.SMOKE_FAMILY_ACCESS_TOKEN;
const keeperEmail = process.env.SMOKE_KEEPER_EMAIL;
const keeperPassword = process.env.SMOKE_KEEPER_PASSWORD;
const audioPath = process.env.SMOKE_AUDIO_PATH;
const timeoutSeconds = Number(process.env.SMOKE_TIMEOUT_SECONDS || '900');
const pollIntervalsMs = [2000, 5000, 10000];

test('audio upload -> transcription -> bilingual title options', async ({ baseURL }) => {
  test.setTimeout(timeoutSeconds * 1000);

  if (!familyToken) throw new Error('SMOKE_FAMILY_ACCESS_TOKEN is required');
  if (!keeperEmail) throw new Error('SMOKE_KEEPER_EMAIL is required');
  if (!keeperPassword) throw new Error('SMOKE_KEEPER_PASSWORD is required');
  if (!audioPath) throw new Error('SMOKE_AUDIO_PATH is required');
  if (!fs.existsSync(audioPath)) throw new Error(`Audio fixture not found: ${audioPath}`);

  const browser = await chromium.launch({
    headless: true,
    executablePath:
      process.env.SMOKE_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  const keeperPage = await context.newPage();
  const appBase = baseURL || 'http://localhost:5173';

  try {
    await page.goto(`${appBase}/f/${familyToken}/capture`);
    await expect(page.getByRole('button', { name: /Upload audio/i })).toBeVisible();
    await page.getByRole('button', { name: /Upload audio/i }).click();
    await expect(page.getByText(/Before we begin/i)).toBeVisible();

    const consentResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response.url().includes(`/f/${familyToken}/stories`) &&
        !response.url().endsWith('/audio')
    );

    await page.getByRole('button', { name: /Yes, they've agreed/i }).click();
    const consentResponse = await consentResponsePromise;
    const story = await consentResponse.json();
    const storyId = story.id;

    await expect(page).toHaveURL(new RegExp(`/f/${familyToken}/capture/upload$`));
    const uploadInput = page.locator('input[type="file"]');
    await uploadInput.setInputFiles(audioPath);
    await expect(page.getByText(path.basename(audioPath), { exact: false })).toBeVisible();
    await page.getByRole('button', { name: /Continue/i }).click();

    await expect(page.getByText(/Quick tag/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Skip for now/i })).toBeVisible();
    await page.getByRole('button', { name: /Skip for now/i }).click();

    await expect(page.getByText(/Confirm & send/i)).toBeVisible();
    await page.getByRole('button', { name: /Send to Keepers/i }).click();
    await expect(page.getByText(/Your story is with the Keepers/i)).toBeVisible();

    await keeperPage.goto(`${appBase}/keeper`);
    await keeperPage.getByLabel('Email').fill(keeperEmail);
    await keeperPage.getByLabel('Password').fill(keeperPassword);
    await keeperPage.getByRole('button', { name: /Sign in/i }).click();
    await expect(keeperPage.getByText(/Review queue/i)).toBeVisible();

    const storyUrl = `${appBase}/keeper/story/${storyId}`;
    const deadline = Date.now() + timeoutSeconds * 1000;
    let storyPage = null;
    let attempt = 0;

    while (Date.now() < deadline) {
      await keeperPage.goto(storyUrl, { waitUntil: 'domcontentloaded' });
      const titleOptions = keeperPage.locator('.title-option-en');
      const suggestionCount = await titleOptions.count();
      if (suggestionCount === 3) {
        storyPage = keeperPage;
        break;
      }
      await keeperPage.waitForTimeout(pollIntervalsMs[Math.min(attempt, pollIntervalsMs.length - 1)]);
      attempt += 1;
    }

    if (!storyPage) {
      throw new Error('Timed out waiting for 3 bilingual title options');
    }

    await expect(storyPage.locator('.title-option-en')).toHaveCount(3);
    await expect(storyPage.locator('.title-option-kh')).toHaveCount(3);
    await expect(storyPage.getByRole('radio')).toHaveCount(4);
    await expect(storyPage.getByRole('radio', { name: /Custom title/i })).toBeVisible();
    await expect(storyPage.locator('.segment-row').first()).toBeVisible();
    await storyPage.getByRole('radio').first().click();
    await expect(storyPage.getByRole('radio').first()).toHaveAttribute('aria-checked', 'true');
  } finally {
    await context.close();
    await browser.close();
  }
});
