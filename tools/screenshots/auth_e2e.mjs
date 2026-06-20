// End-to-end test of the passkey register + login flows using a Chrome virtual
// authenticator (CDP WebAuthn). This is the only way to verify the WebAuthn islands
// (UnifiedLogin, PasskeyRegister) without a physical authenticator.
//
// Usage (note: WebAuthn needs a valid rp_id, so use localhost, not 127.0.0.1):
//   E2E_TESTING=1 venv/bin/python manage.py runserver localhost:8000   # in one shell
//   node tools/screenshots/auth_e2e.mjs                                 # in another
//
// Exit code is non-zero on failure. Relies on the dev-only /_e2e/auth_setup/ hook
// (mainwebsite/e2e_support.py), which is gated behind DEBUG + E2E_TESTING.
import { chromium } from "playwright";

const BASE = process.env.BASE_URL || "http://localhost:8000";

function fail(msg) {
  console.error("E2E FAIL:", msg);
  process.exitCode = 1;
}

const browser = await chromium.launch();
const context = await browser.newContext();
const page = await context.newPage();

const client = await context.newCDPSession(page);
await client.send("WebAuthn.enable");
const { authenticatorId } = await client.send("WebAuthn.addVirtualAuthenticator", {
  options: {
    protocol: "ctap2",
    transport: "internal",
    hasResidentKey: true,
    hasUserVerification: true,
    isUserVerified: true,
    automaticPresenceSimulation: true,
  },
});

// 1) Log the test user in and grant magic-link access (dev-only hook).
const setup = await page.goto(`${BASE}/_e2e/auth_setup/`, { waitUntil: "networkidle" });
if (setup.status() !== 200) {
  fail(`auth_setup returned ${setup.status()} — run the server with E2E_TESTING=1`);
  await browser.close();
  process.exit(1);
}

// 2) Register a passkey.
await page.goto(`${BASE}/passkeys-register/`, { waitUntil: "networkidle" });
await page.waitForTimeout(400);
await page.click('button:has-text("Create Passkey")');
await page.waitForSelector(".alert-success, .alert-danger", { timeout: 8000 });
const regMsg = (await page.textContent(".alert-success, .alert-danger")).trim();
console.log("register:", regMsg);
if (!/created successfully/i.test(regMsg)) fail("registration did not succeed");

const creds = await client.send("WebAuthn.getCredentials", { authenticatorId });
if (creds.credentials.length < 1) fail("no credential stored after registration");

// 3) Log in with that passkey.
await page.goto(`${BASE}/login/`, { waitUntil: "networkidle" });
await page.waitForTimeout(400);
await page.fill("#id_username", "e2euser");
await page.click('button:has-text("Continue")');
await page
  .waitForFunction(() => !window.location.pathname.includes("/login"), {
    timeout: 10000,
  })
  .catch(() => {});
await page.waitForTimeout(400);
if (page.url().includes("/login")) {
  const alert = await page.$(".alert").then((el) => (el ? el.textContent() : ""));
  fail(`still on /login after passkey auth (${(alert || "").trim()})`);
} else {
  console.log("login: redirected to", page.url(), "— passkey auth succeeded");
}

await browser.close();
console.log(process.exitCode ? "E2E: FAILURES" : "E2E: ALL PASSED");
