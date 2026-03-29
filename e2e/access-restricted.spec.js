// @ts-check
const { test, expect } = require("@playwright/test");
const { loginAs } = require("./helpers");

const E2E_EMAIL = process.env.E2E_USER_EMAIL;
const E2E_PASSWORD = process.env.E2E_USER_PASSWORD;

test.describe("Acces restricționat (fără sesiune / fără rol)", () => {
  test("cont și MyPet cer autentificare", async ({ page }) => {
    await page.goto("/cont/");
    await expect(page).toHaveURL(/login/);
    expect(page.url()).toMatch(/next=.*cont/);

    await page.goto("/mypet/");
    await expect(page).toHaveURL(/login/);
  });

  test("publicitate: redirect login", async ({ page }) => {
    await page.goto("/publicitate/");
    await expect(page).toHaveURL(/login/);
  });

  test("admin-analysis: utilizator obișnuit autentificat → redirect Acasă (necesită E2E_USER_*)", async ({
    page,
  }) => {
    test.skip(!E2E_EMAIL || !E2E_PASSWORD, "Setează E2E_USER_EMAIL / E2E_USER_PASSWORD (user non-staff)");

    await loginAs(page, E2E_EMAIL, E2E_PASSWORD);
    await page.goto("/admin-analysis/");
    await expect(page).toHaveURL(/\/$/);
  });
});
