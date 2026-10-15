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

  const findMembership = async (): Promise<string | null> => {
    const url = new URL(`${supabaseUrl}/rest/v1/saathi_household_memberships`);
    url.searchParams.set("auth_user_id", `eq.${user.id}`);
    url.searchParams.set("select", "household_id");
    url.searchParams.set("limit", "1");
    const response = await fetch(url, { headers, cache: "no-store", signal: AbortSignal.timeout(4000) });
    if (!response.ok) throw new Error("household_membership_store_not_configured");
    const rows = await response.json() as Array<{ household_id?: string }>;
    return typeof rows[0]?.household_id === "string" ? rows[0].household_id : null;
  };

  let householdId = await findMembership();
  if (householdId) return { identityId: user.id, householdId };

  const phoneUrl = new URL(`${supabaseUrl}/rest/v1/saathi_households`);
  phoneUrl.searchParams.set("phone_number", `eq.${user.phone}`);
  phoneUrl.searchParams.set("select", "id");
  phoneUrl.searchParams.set("limit", "1");
  const phoneResponse = await fetch(phoneUrl, { headers, cache: "no-store", signal: AbortSignal.timeout(4000) });
  if (!phoneResponse.ok) throw new Error("household_lookup_failed");
  const phoneRows = await phoneResponse.json() as Array<{ id?: string }>;
  // A phone number may have been recycled. Never attach a new Supabase identity
  // to an existing household just because it currently owns the same number.
  const phoneAlreadyAssigned = typeof phoneRows[0]?.id === "string";

  const householdUrl = `${supabaseUrl}/rest/v1/saathi_households${phoneAlreadyAssigned ? "" : "?on_conflict=phone_number"}`;
  const householdResponse = await fetch(householdUrl, {
    method: "POST",
    headers: { ...headers, Prefer: phoneAlreadyAssigned ? "return=representation" : "resolution=ignore-duplicates,return=representation" },
    body: JSON.stringify({
      phone_number: phoneAlreadyAssigned ? null : user.phone,
      memory_consent: false,
      outbound_call_consent: false,
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(4000),
  });
  if (!householdResponse.ok) throw new Error("household_enrollment_failed");
  const householdRows = await householdResponse.json() as Array<{ id?: string }>;
  householdId = typeof householdRows[0]?.id === "string" ? householdRows[0].id : null;

  if (householdId) {
    const membershipUrl = `${supabaseUrl}/rest/v1/saathi_household_memberships?on_conflict=auth_user_id`;
    const membershipResponse = await fetch(membershipUrl, {
      method: "POST",
      headers: { ...headers, Prefer: "resolution=ignore-duplicates,return=representation" },
      body: JSON.stringify({ auth_user_id: user.id, household_id: householdId, verified_phone: user.phone }),
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (!membershipResponse.ok) throw new Error("household_membership_enrollment_failed");
  }

  // Handles concurrent first-login requests: only one membership row can win.
  householdId = await findMembership();
  if (!householdId) throw new Error("household_enrollment_unavailable");
  return { identityId: user.id, householdId };
}
