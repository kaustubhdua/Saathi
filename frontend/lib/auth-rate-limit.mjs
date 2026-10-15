const WINDOW_MS = 15 * 60 * 1000;
const buckets = new Map();

function consume(key, limit, now = Date.now()) {
  let bucket = buckets.get(key);
  if (!bucket || now - bucket.startedAt >= WINDOW_MS) {
    bucket = { startedAt: now, count: 0 };
    buckets.set(key, bucket);
  }
  bucket.count += 1;
  return bucket.count <= limit;
}

export function isAuthRateLimited(request, phone, action) {
  const ip = request.headers.get("x-real-ip") || "unknown";
  const ipLimit = action === "otp" ? 20 : 60;
  const phoneLimit = action === "otp" ? 3 : 10;
  const ipAllowed = consume(`${action}:ip:${ip}`, ipLimit);
  const phoneAllowed = consume(`${action}:phone:${phone}`, phoneLimit);
  if (buckets.size > 5000) {
    const now = Date.now();
    for (const [key, value] of buckets) if (now - value.startedAt >= WINDOW_MS) buckets.delete(key);
  }
  return !ipAllowed || !phoneAllowed;
}

export function _resetAuthRateLimitForTests() {
  buckets.clear();
}
