import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const dashboard = readFileSync(
  fileURLToPath(new URL("../app/dashboard/page.tsx", import.meta.url)),
  "utf8",
);

test("scenario tabs support roving tabindex and keyboard navigation", () => {
  assert.match(dashboard, /tabIndex=\{scenario === id \? 0 : -1\}/);
  assert.match(dashboard, /event\.key === "ArrowRight"/);
  assert.match(dashboard, /event\.key === "ArrowLeft"/);
  assert.match(dashboard, /event\.key === "Home"/);
  assert.match(dashboard, /event\.key === "End"/);
  assert.match(dashboard, /aria-selected=\{scenario === id\}/);
});

test("dynamic API, voice and answer states are announced", () => {
  assert.match(dashboard, /role="status" aria-live="polite"/);
  assert.match(dashboard, /aria-live="polite" aria-atomic="true"/);
  assert.match(dashboard, /aria-pressed=\{voiceState === "listening"\}/);
  assert.match(dashboard, /aria-busy=\{loading\}/);
});

test("dashboard distinguishes persisted consent from automatic memory storage", () => {
  assert.match(dashboard, /Memory consent off/);
  assert.match(dashboard, /Grant permission for future household-memory storage/);
  assert.match(dashboard, /The conversation workflow does not yet write memories automatically/);
  assert.doesNotMatch(dashboard, /Consent-led/);
});
