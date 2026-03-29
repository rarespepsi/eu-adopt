// @ts-check
const { test, expect } = require("@playwright/test");
const { loginAs, logoutViaNavbar } = require("./helpers");

const E2E_EMAIL = process.env.E2E_USER_EMAIL;
const E2E_PASSWORD = process.env.E2E_USER_PASSWORD;

test.describe("Autentificare", () => {
  test("login + cont + logout (necesită E2E_USER_EMAIL / E2E_USER_PASSWORD)", async ({
    page,
  }) => {
    test.skip(!E2E_EMAIL || !E2E_PASSWORD, "Setează E2E_USER_EMAIL și E2E_USER_PASSWORD în mediu");

    await loginAs(page, E2E_EMAIL, E2E_PASSWORD);
    await expect(page).not.toHaveURL(/\/login\//);

    await page.goto("/cont/");
    await expect(page).toHaveURL(/\/cont\/?$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await logoutViaNavbar(page);
    await expect(page).toHaveURL(/\/$/);
  });
});
