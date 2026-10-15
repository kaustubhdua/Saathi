import test from "node:test";
import assert from "node:assert/strict";
import { isAuthRateLimited, _authRateLimitBucketCountForTests, _resetAuthRateLimitForTests } from "../lib/auth-rate-limit.mjs";

const originalEnv = { ...process.env };
test.beforeEach(() => {
  process.env.NODE_ENV = "test";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  _resetAuthRateLimitForTests();
});
test.afterEach(() => {
  for (const key of ["NODE_ENV", "SAATHI_TRUSTED_CLIENT_IP_HEADER"]) {
    if (originalEnv[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnv[key];
  }
  _resetAuthRateLimitForTests();
});

test("OTP sends are limited per phone and per host IP", async () => {
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.15" } });
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543210", "otp"), true);
});

test("OTP verification has a separate attempt budget", async () => {
  const request = new Request("https://saathi.example.com/api/auth/verify", { headers: { "x-real-ip": "192.0.2.16" } });
  for (let i = 0; i < 10; i++) assert.equal(await isAuthRateLimited(request, "+919876543211", "verify"), false);
  assert.equal(await isAuthRateLimited(request, "+919876543211", "verify"), true);
});


test("local rate-limit memory remains hard-bounded under high-cardinality traffic", async () => {
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.17" } });
  for (let i = 0; i < 5200; i++) {
    await isAuthRateLimited(request, `+1${String(i).padStart(10, "0")}`, "otp");
  }
  assert.ok(_authRateLimitBucketCountForTests() <= 5000);
});
