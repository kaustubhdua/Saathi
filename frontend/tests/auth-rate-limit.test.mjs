import test from "node:test";
import assert from "node:assert/strict";
import { isAuthRateLimited, _resetAuthRateLimitForTests } from "../lib/auth-rate-limit.mjs";

test("OTP sends are limited per phone and per host IP", () => {
  _resetAuthRateLimitForTests();
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.15" } });
  assert.equal(isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(isAuthRateLimited(request, "+919876543210", "otp"), false);
  assert.equal(isAuthRateLimited(request, "+919876543210", "otp"), true);
});

test("OTP verification has a separate attempt budget", () => {
  _resetAuthRateLimitForTests();
  const request = new Request("https://saathi.example.com/api/auth/verify", { headers: { "x-real-ip": "192.0.2.16" } });
  for (let i = 0; i < 10; i++) assert.equal(isAuthRateLimited(request, "+919876543211", "verify"), false);
  assert.equal(isAuthRateLimited(request, "+919876543211", "verify"), true);
});
