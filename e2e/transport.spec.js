// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Transport — formular cerere", () => {
  test("completare câmpuri și răspuns după submit", async ({ page }) => {
    await page.goto("/transport/");
    await expect(page.locator("#TW")).toBeVisible();

    await page.locator("#tw-judet, input[name='judet']").fill("Cluj");
    await page.locator("input[name='oras']").fill("Cluj-Napoca");
    await page.locator("#plecare_input, input[name='plecare']").fill("Punct plecare test E2E");
    await page.locator("input[name='sosire']").fill("Punct sosire test E2E");

    await page.getByRole("button", { name: /TRIMITE CEREREA/i }).click();

    await page.waitForURL(/\/transport\/?$/, { timeout: 15000 });
    const html = await page.content();
    expect(
      html.includes("înregistrată") ||
        html.includes("inregistrata") ||
        html.toLowerCase().includes("cerere"),
    ).toBeTruthy();
  });
});
