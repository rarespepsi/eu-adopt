// @ts-check
const { test, expect } = require("@playwright/test");

test.use({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
  userAgent:
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
});

test.describe("PT mobil portrait — butoane și casete", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/pets/", { waitUntil: "networkidle" });
    await expect(page.locator("#PW")).toBeVisible();
    await expect(page.locator("html")).toHaveClass(/pt-phone/, { timeout: 10000 });
  });

  test("structură vizibilă: P1, 3 butoane, 4 pub, grilă P2", async ({ page }) => {
    const p1 = page.locator("#PW .pt-mob-main .pt-cell-1");
    await expect(p1).toBeVisible();
    const p1Box = await p1.boundingBox();
    expect(p1Box?.height).toBeGreaterThanOrEqual(68);
    expect(p1Box?.height).toBeLessThanOrEqual(76);

    await expect(page.locator("#PW .pt-p4-btn-match")).toBeVisible();
    await expect(page.locator("#PW .pt-p4-btn-filters")).toBeVisible();
    await expect(page.locator("#PW .pt-p4-btn-sustine")).toBeVisible();

    const pubSlots = page.locator("#PW .pt-p43-mobil-row .pt-p43-slot");
    await expect(pubSlots).toHaveCount(4);

    const pubRow = page.locator("#PW .pt-p43-mobil-row");
    const pubBox = await pubRow.boundingBox();
    expect(pubBox?.height).toBeGreaterThanOrEqual(68);
    expect(pubBox?.height).toBeLessThanOrEqual(76);

    const grid = page.locator("#pt_p2_grid");
    await expect(grid).toBeVisible();
    const cols = await grid.evaluate((el) => getComputedStyle(el).gridTemplateColumns);
    expect(cols.split(" ").length).toBe(2);

    await expect(page.locator("#pt_p2_grid .pt-p2-card-cell").first()).toBeVisible();
  });

  test("buton Filtre deschide panoul + taburi specie + selecturi + OK", async ({ page }) => {
    const filtreBtn = page.locator("#PW .pt-p4-btn-filters");
    await filtreBtn.click();
    await expect(page.locator("#P4")).toHaveClass(/pt-mobile-filters-open/);

    const filtersBox = page.locator("#P4 .pt-p4-box-filters");
    await expect(filtersBox).toBeVisible();

    for (const label of ["Toate", "Câini", "Pisici", "Altele"]) {
      await expect(page.locator("#pt_animal_filter_tabs").getByRole("link", { name: new RegExp(label) })).toBeVisible();
    }

    await expect(page.locator("#id_judet_pt")).toBeVisible();
    await expect(page.locator("#id_marime_pt")).toBeVisible();
    await expect(page.locator("#id_varsta_pt")).toBeVisible();
    await expect(page.locator("#id_sex_pt")).toBeVisible();

    await page.locator("#id_judet_pt").selectOption({ index: 1 });

    await page.locator("#pt_animal_filter_tabs a[data-pt-species='dog']").click({ force: true });
    await expect(page.locator("#pt_filter_species_field")).toHaveValue("dog");

    await expect(page.locator("#ptMobileFiltersOk")).toBeVisible();

    await page.locator("#ptMobileFiltersClose").click();
    await expect(page.locator("#P4")).not.toHaveClass(/pt-mobile-filters-open/);
  });

  test("Găsește-mi perechea deschide modalul match", async ({ page }) => {
    const matchBtn = page.locator("#PW .pt-p4-btn-match");
    if ((await matchBtn.count()) === 0) {
      test.skip(true, "Buton match ascuns (species=other)");
    }
    await matchBtn.click();
    const modal = page.locator("#ptMatchModal");
    await expect(modal).toBeVisible();
    await expect(modal.locator(".pt-match-modal__title")).toHaveText(/Găsește-mi perechea/);
    await expect(modal.locator('input[type="checkbox"]').first()).toBeVisible();
    await expect(modal.locator(".pt-match-modal__submit")).toBeVisible();
    await page.locator("#ptMatchModalClose").click();
    await expect(modal).toBeHidden();
  });

  test("Ajută un Suflet navighează la donații", async ({ page }) => {
    await page.locator("#PW .pt-p4-btn-sustine").click();
    await expect(page).toHaveURL(/\/donatii/);
  });

  test("card P2: link profil, wish, scroll pagină", async ({ page }) => {
    const firstCard = page.locator("#pt_p2_grid .pt-p2-card-cell").first();
    await expect(firstCard).toBeVisible();

    const profileLink = firstCard.locator("a.pt-p2-card-link");
    await expect(profileLink).toBeVisible();
    const href = await profileLink.getAttribute("href");
    expect(href).toMatch(/\/pets\/\d+\/?/);

    const wishBtn = firstCard.locator(".pt-p2-wish-btn");
    if (await wishBtn.count()) {
      await wishBtn.click({ force: true });
    }

    const canScroll = await page.evaluate(
      () => document.documentElement.scrollHeight > window.innerHeight + 80
    );
    if (canScroll) {
      const before = await page.evaluate(() => window.scrollY);
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await page.waitForTimeout(200);
      const after = await page.evaluate(() => window.scrollY);
      expect(after).toBeGreaterThan(before);
    }
  });

  test("bandă P1 cursivă — casete vizibile", async ({ page }) => {
    const p1Items = page.locator("#PW .pt-mob-main .pt-cell-1 .pt-strip-item");
    await expect(p1Items.first()).toBeVisible();
    expect(await p1Items.count()).toBeGreaterThan(0);
  });

  test("casete pub au link sau conținut vizibil", async ({ page }) => {
    const slots = page.locator("#PW .pt-p43-mobil-row .pt-p43-slot");
    const count = await slots.count();
    expect(count).toBe(4);
    for (let i = 0; i < count; i++) {
      const slot = slots.nth(i);
      await expect(slot).toBeVisible();
      const box = await slot.boundingBox();
      expect(box?.width).toBeGreaterThan(20);
      expect(box?.height).toBeGreaterThan(20);
    }
  });

  test("scroll infinit P2 — sentinel vizibil când există mai mult", async ({ page }) => {
    const sentinel = page.locator("#pt_p2_load_sentinel");
    const hasMore = await page.locator("#pt_p2_grid").getAttribute("data-p2-has-more");
    if (hasMore === "1") {
      await sentinel.scrollIntoViewIfNeeded();
      await page.waitForTimeout(800);
      const countAfter = await page.locator("#pt_p2_grid .pt-p2-card-cell").count();
      expect(countAfter).toBeGreaterThanOrEqual(24);
    }
  });
});
