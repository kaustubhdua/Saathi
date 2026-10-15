import { proxyRequest } from "../../../lib/backend-proxy.mjs";
import { resolveVerifiedHouseholdContext } from "../../../lib/household-identity";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: Request, context: RouteContext) {
  const { path = [] } = await context.params;
  const routePath = path.join("/");
  const identityRoutes = new Set(["api/v1/agent", "api/v1/voice/turn", "api/v1/household/consent"]);
  let verifiedContext = null;
  if (identityRoutes.has(routePath)) {
    try {
      verifiedContext = await resolveVerifiedHouseholdContext();
    } catch {
      return Response.json(
        { detail: "household_identity_unavailable" },
        { status: 503, headers: { "Cache-Control": "no-store" } },
      );
    }
  }
  if (routePath === "api/v1/household/consent" && !verifiedContext) {
    return Response.json(
      { detail: "verified_phone_identity_required" },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }
  return proxyRequest(request, path, verifiedContext);
}

export const GET = handle;
export const POST = handle;
