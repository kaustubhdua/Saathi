import { createSupabaseServerClient } from "./supabase/server";

export type VerifiedHouseholdContext = {
  identityId: string;
  householdId: string;
};

const E164 = /^\+[1-9]\d{7,14}$/;

export async function resolveVerifiedHouseholdContext(): Promise<VerifiedHouseholdContext | null> {
  const auth = await createSupabaseServerClient();
  if (!auth) return null;

  const { data, error } = await auth.auth.getUser();
  if (error || !data.user) return null;
  const user = data.user;
  if (!user.phone || !user.phone_confirmed_at || !E164.test(user.phone)) {
    throw new Error("verified_phone_identity_required");
  }

  const supabaseUrl = (process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || "").replace(/\/$/, "");
  const secret = process.env.SUPABASE_SECRET_KEY;
  if (!supabaseUrl || !secret) throw new Error("household_store_not_configured");

  const headers = {
    apikey: secret,
    Authorization: `Bearer ${secret}`,
    Accept: "application/json",
    "Content-Type": "application/json",
  };

  const findHousehold = async (): Promise<string | null> => {
    const url = new URL(`${supabaseUrl}/rest/v1/saathi_households`);
    url.searchParams.set("phone_number", `eq.${user.phone}`);
    url.searchParams.set("select", "id");
    url.searchParams.set("limit", "1");
    const response = await fetch(url, { headers, cache: "no-store", signal: AbortSignal.timeout(4000) });
    if (!response.ok) throw new Error("household_lookup_failed");
    const rows = await response.json() as Array<{ id?: string }>;
    return typeof rows[0]?.id === "string" ? rows[0].id : null;
  };

  let householdId = await findHousehold();
  if (!householdId) {
    const url = `${supabaseUrl}/rest/v1/saathi_households?on_conflict=phone_number`;
    const response = await fetch(url, {
      method: "POST",
      headers: { ...headers, Prefer: "resolution=ignore-duplicates,return=representation" },
      body: JSON.stringify({
        phone_number: user.phone,
        memory_consent: false,
        outbound_call_consent: false,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (!response.ok) throw new Error("household_enrollment_failed");
    const rows = await response.json() as Array<{ id?: string }>;
    householdId = typeof rows[0]?.id === "string" ? rows[0].id : await findHousehold();
  }
  if (!householdId) throw new Error("household_enrollment_unavailable");
  return { identityId: user.id, householdId };
}
