// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Fișă animal din listă", () => {
  test("din Prietenul tău: primul card duce la fișă; elemente importante vizibile", async ({
    page,
  }) => {
    await page.goto("/pets/");
    const card = page.locator("a.pt-p2-card-link").first();
    await expect(card).toBeVisible({ timeout: 15000 });
    await card.click();

    await expect(page).toHaveURL(/\/pets\/\d+\/?$/);

    await expect(page.locator("#petCardCopyBtn")).toBeVisible();
    // #petAdoptCorner apare doar pentru utilizator autentificat care poate adopta (nu pentru anonim).
    await expect(page.locator("#petQrCorner")).toBeVisible({ timeout: 10000 });
    await expect(page.getByLabel("Stare adopție")).toBeVisible();
  });
});
