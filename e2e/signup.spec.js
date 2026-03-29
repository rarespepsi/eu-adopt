// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Înregistrare PF", () => {
  test("pagina signup PF și validări vizibile la submit incomplet", async ({ page }) => {
    await page.goto("/signup/persoana-fizica/");
    await expect(page).toHaveURL(/\/signup\/persoana-fizica\/?$/);

    await page.getByRole("button", { name: "Creează cont" }).click();

    const body = page.locator("body");
    await expect(body).toContainText(/obligatoriu|Email|Parolă|Trebuie/i);
  });
});
