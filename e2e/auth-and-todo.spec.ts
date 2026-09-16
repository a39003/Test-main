import { test, expect } from "@playwright/test";

test.describe("Tier 2B: E2E Testing Strategy & Verification", () => {
  test("Scenario 1: Full User Journey (Register -> Create Todo -> Toggle Complete -> Verify UI -> Logout)", async ({
    page,
  }) => {
    const ts = Date.now();
    const user = {
      email: `e2e_journey_${ts}@example.com`,
      password: "Password123!",
    };

    // 1. Go to Register Page
    await page.goto("/register");
    await page.fill("#email", user.email);
    await page.fill("#password", user.password);
    await page.fill("#confirmPassword", user.password);
    await page.click('button[type="submit"]');

    // 2. Should redirect to Dashboard (/) after registration
    await expect(page).toHaveURL("/");
    await expect(page.getByText("My Todos")).toBeVisible();
    await expect(page.getByText(user.email)).toBeVisible();

    // 3. Create a new Todo item
    const todoTitle = `Full Journey Todo ${ts}`;
    const todoDesc = "Description for full user journey test";

    await page.click('button:has-text("Add Todo")');
    await page.fill("#title", todoTitle);
    await page.fill("#description", todoDesc);
    await page.click('form button[type="submit"]');

    // 4. Verify Todo item is created and visible in UI
    await expect(page.getByText(todoTitle)).toBeVisible();
    await expect(page.getByText(todoDesc)).toBeVisible();

    // 5. Toggle completion status
    const todoCheckbox = page.locator('button[role="checkbox"]').first();
    await todoCheckbox.click();

    // Verify completion status (checkbox checked & title has line-through style)
    await expect(todoCheckbox).toHaveAttribute("data-state", "checked");
    await expect(page.getByText(todoTitle)).toHaveClass(/line-through/);

    // 6. Logout
    await page.click('button:has-text("Logout")');

    // Verify redirected back to Login page
    await expect(page).toHaveURL("/login");
    await expect(page.getByText("Welcome Back")).toBeVisible();
  });

  test("Scenario 2: Cross-User Data Isolation (User A private todo is NOT visible to User B)", async ({
    browser,
  }) => {
    const ts = Date.now();
    const userA = {
      email: `e2e_iso_a_${ts}@example.com`,
      password: "Password123!",
    };
    const userB = {
      email: `e2e_iso_b_${ts}@example.com`,
      password: "Password123!",
    };

    // Create Context A for User A
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();

    // User A registers & logs in
    await pageA.goto("/register");
    await pageA.fill("#email", userA.email);
    await pageA.fill("#password", userA.password);
    await pageA.fill("#confirmPassword", userA.password);
    await pageA.click('button[type="submit"]');
    await expect(pageA).toHaveURL("/");

    // User A creates a private todo
    const privateTodoTitle = `User A Secret Todo ${ts}`;
    await pageA.click('button:has-text("Add Todo")');
    await pageA.fill("#title", privateTodoTitle);
    await pageA.click('form button[type="submit"]');
    await expect(pageA.getByText(privateTodoTitle)).toBeVisible();

    // Create Context B for User B (separate isolated session/cookies)
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();

    // User B registers & logs in
    await pageB.goto("/register");
    await pageB.fill("#email", userB.email);
    await pageB.fill("#password", userB.password);
    await pageB.fill("#confirmPassword", userB.password);
    await pageB.click('button[type="submit"]');
    await expect(pageB).toHaveURL("/");
    await expect(pageB.getByText(userB.email)).toBeVisible();

    // Verify User B CANNOT see User A's private todo item
    await expect(pageB.getByText(privateTodoTitle)).not.toBeVisible();

    // Cleanup contexts
    await contextA.close();
    await contextB.close();
  });
});
