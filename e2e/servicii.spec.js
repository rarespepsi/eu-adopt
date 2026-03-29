// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Servicii", () => {
  test("pagina principală Servicii se încarcă", async ({ page }) => {
    await page.goto("/servicii/");
    await expect(page.getByRole("main", { name: "Conținut Servicii" })).toBeVisible();
    await expect(page.locator("#S1")).toBeVisible();
  });
});
