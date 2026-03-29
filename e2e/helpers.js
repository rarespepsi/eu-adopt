/**
 * @param {import('@playwright/test').Page} page
 * @param {string} email
 * @param {string} password
 */
async function loginAs(page, email, password) {
  await page.goto("/login/");
  await page.locator("#id_login").fill(email);
  await page.locator("#id_password").fill(password);
  await page.locator("button.login-submit").click();
}

/**
 * @param {import('@playwright/test').Page} page
 */
async function logoutViaNavbar(page) {
  await page.getByRole("link", { name: /^Logout$/i }).click();
}

module.exports = { loginAs, logoutViaNavbar };
