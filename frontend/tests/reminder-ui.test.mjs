import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const dashboard = readFileSync(fileURLToPath(new URL("../app/dashboard/page.tsx", import.meta.url)), "utf8");
const proxy = readFileSync(fileURLToPath(new URL("../lib/backend-proxy.mjs", import.meta.url)), "utf8");

test("scheduled reminders are opt-in and shown as in-app only", () => {
  assert.match(dashboard, /capabilities\.reminders_configured === true/);
  assert.match(dashboard, /type="datetime-local"/);
  assert.match(dashboard, /scheduled_callback: scheduledDate\.toISOString\(\)/);
  assert.match(dashboard, /Saathi will not place a phone call/);
  assert.match(dashboard, /Automatic reminders are disabled until database migration/);
});

test("notifications are polled and read through verified household proxy routes", () => {
  assert.match(dashboard, /fetch\("\/backend\/api\/v1\/household\/notifications"/);
  assert.match(dashboard, /fetch\("\/backend\/api\/v1\/household\/notifications\/read"/);
  assert.match(dashboard, /setInterval\(\(\) => void loadNotifications\(\), 30_000\)/);
  assert.match(proxy, /"api\/v1\/household\/notifications":/);
  assert.match(proxy, /"api\/v1\/household\/notifications\/read":/);
  assert.match(proxy, /api\/v1\/household\/notifications", "api\/v1\/household\/notifications\/read"/);
});