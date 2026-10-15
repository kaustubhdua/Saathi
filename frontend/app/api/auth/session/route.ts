import { createSupabaseServerClient } from "../../../../lib/supabase/server";

export async function GET() {
  const supabase = await createSupabaseServerClient();
  if (!supabase) return Response.json({ authenticated: false, authConfigured: false }, { headers: { "Cache-Control": "no-store" } });
  const { data, error } = await supabase.auth.getUser();
  const user = !error ? data.user : null;
  const phone = user?.phone_confirmed_at && user.phone ? user.phone : null;
  return Response.json({
    authenticated: Boolean(user),
    phoneVerified: Boolean(phone),
    phoneSuffix: phone ? phone.slice(-4) : null,
  }, { headers: { "Cache-Control": "no-store" } });
}
