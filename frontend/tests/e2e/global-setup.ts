// Runs once before the suite (after both web servers are up):
//
// 1. Compiles every page route of the Next.js dev server. `next dev` compiles a route on its
//    first visit; on a busy machine that first compile can take longer than an assertion's
//    5-second wait (seen in Phase 7D: a saved delivery whose case page was still compiling).
//    Requesting each route once here moves that cost out of the tests without raising any
//    test timeout. Dynamic segments use a placeholder ID: the page compiles even though the
//    API would answer 404 for it.
// 2. Signs the synthetic e2e reviewer in once (provisioned by the webServer command in
//    playwright.config.ts) and saves the session for the review specs. One login for the
//    whole run.

import { request, type FullConfig } from "@playwright/test";
import { REVIEWER_EMAIL, REVIEWER_PASSWORD, REVIEWER_STATE } from "./helpers";

const PLACEHOLDER_ID = "00000000-0000-4000-8000-000000000000";
const ROUTES = [
  "/",
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/app",
  "/app/cases",
  "/app/cases/new",
  `/app/cases/${PLACEHOLDER_ID}`,
  `/app/cases/${PLACEHOLDER_ID}/evidence`,
  `/app/cases/${PLACEHOLDER_ID}/responses`,
  `/app/cases/${PLACEHOLDER_ID}/checklist`,
  `/app/cases/${PLACEHOLDER_ID}/interest`,
  `/app/cases/${PLACEHOLDER_ID}/timeline`,
  "/app/onboarding",
  "/app/settings",
  "/app/review",
  `/app/review/${PLACEHOLDER_ID}`,
];

export default async function globalSetup(config: FullConfig) {
  const baseURL = String(config.projects[0].use.baseURL);
  const context = await request.newContext({ baseURL });

  for (const route of ROUTES) {
    const page = await context.get(route, { timeout: 180_000 });
    if (page.status() !== 200) throw new Error(`Warm-up of ${route} failed: ${page.status()}`);
  }

  const response = await context.post("/api/v1/auth/login", {
    headers: { Origin: new URL(baseURL).origin, "X-PaySetu-Client": "web" },
    data: { email: REVIEWER_EMAIL, password: REVIEWER_PASSWORD },
  });
  if (response.status() !== 200) {
    throw new Error(`Reviewer login failed: ${response.status()} ${await response.text()}`);
  }
  await context.storageState({ path: REVIEWER_STATE });
  await context.dispose();
}
