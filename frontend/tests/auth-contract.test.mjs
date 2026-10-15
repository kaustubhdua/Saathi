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
const pinRoute = read("../app/api/auth/household-pin/route.ts");
const signoutRoute = read("../app/api/auth/signout/route.ts");
const membershipMigration = read("../../docs/proposed-migrations/20261015080000_saathi_household_memberships.sql.proposed");

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
  assert.match(proxyRoute, /requiresUserAction \? 401 : 503/);
});

test("household PIN is separate, rate-limited and server-keyed", () => {
  assert.match(pinRoute, /isAuthRateLimited\(request, user\.phone, "pin"\)/);
  assert.match(pinRoute, /isStrongHouseholdPin\(body\.pin\)/);
  assert.match(identity, /const ascending = digits\.every/);
  assert.match(identity, /const descending = digits\.every/);
  assert.match(pinRoute, /verifyHouseholdPin\(user\.id, body\.pin, existing\.pin_hash\)/);
  assert.match(pinRoute, /setHouseholdContextCookie\(user\.id, membership\.household_id\)/);
  assert.match(identity, /HOUSEHOLD_PIN_PEPPER/);
  assert.match(identity, /HOUSEHOLD_CONTEXT_SIGNING_SECRET/);
  assert.match(identity, /httpOnly: true/);
  assert.match(signoutRoute, /clearHouseholdContextCookie/);
});

test("proposed membership migration denies browser access and remains syntactically complete", () => {
  assert.match(membershipMigration, /auth_user_id uuid NOT NULL UNIQUE REFERENCES auth\.users\(id\)/);
  assert.ok(membershipMigration.includes("pin_hash text NOT NULL CHECK (pin_hash ~ '^[0-9a-f]{64}$')"));
  assert.ok(membershipMigration.includes("verified_phone text NOT NULL CHECK"));
  assert.ok(membershipMigration.includes("[0-9]{7,14}$')"));
  assert.match(membershipMigration, /ENABLE ROW LEVEL SECURITY/);
  assert.match(membershipMigration, /REVOKE ALL ON TABLE public\.saathi_household_memberships FROM PUBLIC, anon, authenticated/);
  assert.match(membershipMigration, /GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public\.saathi_household_memberships TO service_role/);
  assert.match(membershipMigration, /PROPOSED ONLY/);
  assert.equal(membershipMigration.trim().endsWith(";"), true);
  assert.equal((membershipMigration.match(/CREATE INDEX/g) || []).length, 1);
});


test("phone-number uniqueness races never attach a new Auth user to an existing household", () => {
  assert.match(identity, /if \(!householdId && !phoneAlreadyAssigned\) \{/);
  assert.match(identity, /isolatedHouseholdResponse/);
  assert.match(identity, /phone_number: null, memory_consent: false, outbound_call_consent: false/);
  assert.doesNotMatch(identity, /if \(!householdId && !phoneAlreadyAssigned\) householdId = await findHouseholdByPhone/);
});
