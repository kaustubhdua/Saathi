import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8");
const server = read("../lib/supabase/server.ts");
const identity = read("../lib/household-identity.ts");
const login = read("../app/login/page.tsx");
const proxyRoute = read("../app/backend/[...path]/route.ts");
const consentRoute = read("../app/api/auth/verify/route.ts");

test("Supabase SSR auth uses cookie sessions and publishable key only", () => {
  assert.match(server, /createServerClient/);
  assert.match(server, /cookieStore\.getAll\(\)/);
  assert.match(server, /NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY/);
  assert.doesNotMatch(server, /SUPABASE_SECRET_KEY/);
});

test("household binding requires confirmed E.164 phone and server-only secret", () => {
  assert.match(identity, /phone_confirmed_at/);
  assert.match(identity, /E164/);
  assert.match(identity, /SUPABASE_SECRET_KEY/);
  assert.match(identity, /saathi_household_memberships/);
  assert.match(identity, /auth_user_id/);
  assert.match(identity, /phoneAlreadyAssigned/);
  assert.match(identity, /memory_consent: false/);
  assert.match(identity, /outbound_call_consent: false/);
  assert.doesNotMatch(identity, /NEXT_PUBLIC_SUPABASE_SECRET_KEY/);
});

test("OTP flow requires a verified six-digit SMS code", () => {
  assert.match(login, /\/api\/auth\/otp/);
  assert.match(login, /\/api\/auth\/verify/);
  assert.match(login, /autoComplete="one-time-code"/);
  assert.match(consentRoute, /verifyOtp/);
  assert.match(consentRoute, /phone_confirmed_at/);
});

test("proxy resolves household context server-side and protects consent routes", () => {
  assert.match(proxyRoute, /resolveVerifiedHouseholdContext/);
  assert.match(proxyRoute, /api\/v1\/household\/consent/);
  assert.match(proxyRoute, /household_identity_unavailable/);
  assert.match(proxyRoute, /household_pin_verification_required/);
  assert.match(proxyRoute, /api\/v1\/household\/tasks/);
  assert.match(proxyRoute, /api\/v1\/household\/memories/);
  assert.match(proxyRoute, /api\/v1\/household\/help-cases/);
  assert.match(proxyRoute, /requiresUserAction \? 401 : 503/);
});
