import { createSupabaseServerClient } from "../../../../lib/supabase/server";

function validOrigin(request: Request) {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  try { return new URL(origin).origin === new URL(request.url).origin; } catch { return false; }
}

export async function POST(request: Request) {
  if (!validOrigin(request)) return Response.json({ detail: "origin_not_allowed" }, { status: 403 });
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 4096) return Response.json({ detail: "request_body_too_large" }, { status: 413 });
  let body: { phone?: unknown };
  try {
    const raw = await request.text();
    if (raw.length > 4096) return Response.json({ detail: "request_body_too_large" }, { status: 413 });
    body = JSON.parse(raw);
  } catch {
    return Response.json({ detail: "invalid_json" }, { status: 400 });
  }
  if (typeof body.phone !== "string" || !/^\+[1-9]\d{7,14}$/.test(body.phone)) {
    return Response.json({ detail: "valid_e164_phone_required" }, { status: 422 });
  }

  const supabase = await createSupabaseServerClient();
  if (!supabase) return Response.json({ detail: "supabase_auth_not_configured" }, { status: 503 });
  const { error } = await supabase.auth.signInWithOtp({ phone: body.phone, options: { shouldCreateUser: true } });
  if (error) {
    const status = error.status === 429 ? 429 : 503;
    return Response.json({ detail: status === 429 ? "otp_rate_limited" : "otp_delivery_unavailable" }, { status });
  }
  return Response.json({ status: "otp_requested" }, { headers: { "Cache-Control": "no-store" } });
}
