import test from "node:test";
import assert from "node:assert/strict";
import { isAuthRateLimited, _resetAuthRateLimitForTests } from "../lib/auth-rate-limit.mjs";

const originalEnv = { ...process.env };
const originalFetch = globalThis.fetch;
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
  globalThis.fetch = originalFetch;
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


test("production OTP limits fail closed without shared Redis configuration", async () => {
  process.env.NODE_ENV = "production";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  delete process.env.UPSTASH_REDIS_REST_URL;
  delete process.env.UPSTASH_REDIS_REST_TOKEN;
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.25" } });
  await assert.rejects(isAuthRateLimited(request, "+919876543212", "otp"), /shared_rate_limit_not_configured/);
});

test("production OTP limits use atomic shared counters and hash identity keys", async () => {
  process.env.NODE_ENV = "production";
  process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER = "x-real-ip";
  process.env.UPSTASH_REDIS_REST_URL = "https://saathi-test.upstash.io";
  process.env.UPSTASH_REDIS_REST_TOKEN = "test-only-token-never-used-outside-this-unit-test";
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options, command: JSON.parse(options.body) });
    return Response.json({ result: calls.length === 1 ? 4 : 1 });
  };
  const request = new Request("https://saathi.example.com/api/auth/otp", { headers: { "x-real-ip": "192.0.2.26" } });
  assert.equal(await isAuthRateLimited(request, "+919876543213", "otp"), true);
  assert.equal(calls.length, 2);
  assert.ok(calls.every((call) => call.url === "https://saathi-test.upstash.io"));
  assert.ok(calls.every((call) => String(call.command[3]).startsWith("saathi:auth:v1:")));
  assert.ok(calls.every((call) => !JSON.stringify(call.command).includes("+919876543213")));
});
