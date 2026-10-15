import { createHmac } from "node:crypto";
import { isIP } from "node:net";

const WINDOW_MS = 15 * 60 * 1000;
const buckets = new Map();
const RATE_LIMIT_SCRIPT = "local count = redis.call('INCR', KEYS[1]); if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; return count";

function consume(key, limit, now = Date.now()) {
  let bucket = buckets.get(key);
  if (!bucket || now - bucket.startedAt >= WINDOW_MS) {
    bucket = { startedAt: now, count: 0 };
    buckets.set(key, bucket);
  }
  bucket.count += 1;
  return bucket.count <= limit;
}

function sharedConfiguration(env) {
  const rawUrl = env.UPSTASH_REDIS_REST_URL?.trim();
  const token = env.UPSTASH_REDIS_REST_TOKEN?.trim();
  if (!rawUrl || !token) return null;
  try {
    const url = new URL(rawUrl);
    if (url.protocol !== "https:" || !url.hostname.endsWith(".upstash.io") || url.port || url.username || url.password || url.pathname !== "/" || url.search || url.hash) return null;
    return { url: url.origin, token };
  } catch {
    return null;
  }
}

async function sharedLimit(key, limit, configuration) {
  const digest = createHmac("sha256", configuration.token).update(key).digest("hex");
  const response = await fetch(configuration.url, {
    method: "POST",
    headers: {
      authorization: `Bearer ${configuration.token}`,
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify(["EVAL", RATE_LIMIT_SCRIPT, "1", `saathi:auth:v1:${digest}`, String(Math.ceil(WINDOW_MS / 1000))]),
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(2500),
  });
  if (!response.ok) throw new Error("auth_rate_limit_unavailable");
  const payload = await response.json();
  if (typeof payload?.result !== "number" || !Number.isSafeInteger(payload.result) || payload.result < 1) {
    throw new Error("auth_rate_limit_invalid_response");
  }
  return payload.result <= limit;
}

export async function isAuthRateLimited(request, phone, action) {
  const ipHeader = process.env.SAATHI_TRUSTED_CLIENT_IP_HEADER?.trim().toLowerCase();
  if (!ipHeader || !["x-real-ip", "x-forwarded-for", "x-vercel-forwarded-for", "cf-connecting-ip"].includes(ipHeader)) {
    if (process.env.NODE_ENV === "production") throw new Error("trusted_client_ip_not_configured");
  }
  const rawIp = ipHeader ? request.headers.get(ipHeader)?.trim() : "";
  const ip = rawIp && !rawIp.includes(",") && isIP(rawIp) ? rawIp : "unknown";
  const phoneLimit = action === "otp" ? 3 : action === "pin" ? 5 : 10;
  const ipLimit = action === "otp" ? 20 : 60;

  if (process.env.NODE_ENV === "production") {
    const configuration = sharedConfiguration(process.env);
    if (!configuration) throw new Error("shared_rate_limit_not_configured");
    const [phoneAllowed, ipAllowed] = await Promise.all([
      sharedLimit(`${action}:phone:${phone}`, phoneLimit, configuration),
      sharedLimit(`${action}:ip:${ip}`, ipLimit, configuration),
    ]);
    return !phoneAllowed || !ipAllowed;
  }

  const phoneAllowed = consume(`${action}:phone:${phone}`, phoneLimit);
  const ipAllowed = consume(`${action}:ip:${ip}`, ipLimit);
  if (buckets.size > 5000) {
    const now = Date.now();
    for (const [key, value] of buckets) {
      if (now - value.startedAt >= WINDOW_MS) buckets.delete(key);
    }
    while (buckets.size > 5000) {
      const oldest = buckets.keys().next().value;
      if (oldest === undefined) break;
      buckets.delete(oldest);
    }
  }
  return !phoneAllowed || !ipAllowed;
}

export function _resetAuthRateLimitForTests() {
  buckets.clear();
}

export function _authRateLimitBucketCountForTests() {
  return buckets.size;
}
