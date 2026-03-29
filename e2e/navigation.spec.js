// @ts-check
const { test, expect } = require("@playwright/test");

test.describe("Navigare principală (navbar)", () => {
  test("paginile cheie se încarcă din meniu", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Acasă", exact: true }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.getByRole("link", { name: "Prietenul tău" }).click();
    await expect(page).toHaveURL(/\/pets\/?$/);

    await page.getByRole("link", { name: "Servicii" }).click();
    await expect(page).toHaveURL(/\/servicii\/?$/);

    await page.getByRole("link", { name: "Transport" }).click();
    await expect(page).toHaveURL(/\/transport\/?$/);

    await page.getByRole("link", { name: "Shop" }).click();
    await expect(page).toHaveURL(/\/shop\/?$/);

    await page.getByRole("link", { name: "Contact" }).click();
    await expect(page).toHaveURL(/\/contact\/?$/);

    await page.getByRole("link", { name: "Termeni și condiții" }).click();
    await expect(page).toHaveURL(/\/termeni-si-conditii\/?$/);
  });
});
