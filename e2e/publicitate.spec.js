// @ts-check
const { test, expect } = require("@playwright/test");
const { loginAs } = require("./helpers");

const PUB_EMAIL = process.env.E2E_PUB_EMAIL;
const PUB_PASSWORD = process.env.E2E_PUB_PASSWORD;

test.describe("Publicitate", () => {
  test("anonim: /publicitate/ duce la login (next)", async ({ page }) => {
    await page.goto("/publicitate/");
    await expect(page).toHaveURL(/login/);
    expect(page.url()).toContain("next=");
  });

  test("utilizator autorizat (staff/colab): slot, perioadă, coș — necesită E2E_PUB_EMAIL / E2E_PUB_PASSWORD", async ({
    page,
  }) => {
    test.skip(!PUB_EMAIL || !PUB_PASSWORD, "Setează E2E_PUB_EMAIL și E2E_PUB_PASSWORD (cont colaborator sau staff)");

    await loginAs(page, PUB_EMAIL, PUB_PASSWORD);
    await page.goto("/publicitate/");
    await expect(page.locator("#PUBW")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Coș publicitate" })).toBeVisible();

    await page.getByRole("link", { name: "PT", exact: true }).click();
    await expect(page).toHaveURL(/sect=pt/);

    await page.locator('[data-slot="P4.3"]').click({ timeout: 15000 });

    await expect(page.locator("#pubDetailsForm")).toBeVisible({ timeout: 10000 });
    await page.locator("#pubQty").fill("2");
    await page.locator("#pubAddBtn").click();

    const total = page.locator("#pubCartTotal");
    await expect(total).not.toHaveText("0 lei", { timeout: 8000 });
  });
});
