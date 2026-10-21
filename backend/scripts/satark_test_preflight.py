"""Fail-closed preflight for dedicated SATARK test identities.

This verifies only secret provisioning, project identity, and Supabase Auth login.
It deliberately does NOT claim tenant isolation or authorization acceptance; those
require requests against the application's authenticated API and are a separate gate.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse
from uuid import UUID

EXPECTED_PROJECT_REF = "ibvgxgvcqcfnoyrlwywa"


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing_required_secret:{name}")
    return value


def uuid_value(name: str) -> str:
    try:
        return str(UUID(required(name)))
    except ValueError as exc:
        raise RuntimeError(f"invalid_uuid_secret:{name}") from exc


def login(base_url: str, api_key: str, email: str, password: str, label: str) -> str:
    body = json.dumps({"email": email, "password": password}).encode()
    request = urllib.request.Request(
        f"{base_url}/auth/v1/token?grant_type=password",
        data=body,
        headers={"apikey": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        # Never emit provider response bodies, which can contain sensitive details.
        raise RuntimeError(f"supabase_auth_login_failed:{label}:http_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError(f"supabase_auth_login_failed:{label}:network_or_invalid_response") from None
    user = payload.get("user") if isinstance(payload, dict) else None
    user_id = user.get("id") if isinstance(user, dict) else None
    if not isinstance(user_id, str):
        raise RuntimeError(f"supabase_auth_login_failed:{label}:user_id_missing")
    try:
        return str(UUID(user_id))
    except ValueError:
        raise RuntimeError(f"supabase_auth_login_failed:{label}:user_id_invalid") from None


def main() -> int:
    raw_url = required("SATARK_TEST_SUPABASE_URL").rstrip("/")
    api_key = required("SATARK_TEST_SUPABASE_PUBLISHABLE_KEY")
    parsed = urlparse(raw_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError("test_supabase_url_must_be_https")
    match = re.fullmatch(r"([a-z0-9-]+)\.supabase\.co", parsed.hostname)
    if not match or match.group(1) != EXPECTED_PROJECT_REF:
        raise RuntimeError("test_supabase_project_ref_mismatch")

    tenant_a = uuid_value("SATARK_TEST_TENANT_A_ID")
    tenant_b = uuid_value("SATARK_TEST_TENANT_B_ID")
    tenant_viewer = uuid_value("SATARK_TEST_VIEWER_TENANT_ID")
    if len({tenant_a, tenant_b}) != 2:
        raise RuntimeError("tenant_a_and_b_must_be_distinct")
    if tenant_viewer not in {tenant_a, tenant_b}:
        raise RuntimeError("viewer_tenant_must_match_one_test_tenant")

    users = [
        ("user_a", required("SATARK_TEST_USER_A_EMAIL"), required("SATARK_TEST_USER_A_PASSWORD")),
        ("user_b", required("SATARK_TEST_USER_B_EMAIL"), required("SATARK_TEST_USER_B_PASSWORD")),
        ("viewer", required("SATARK_TEST_VIEWER_EMAIL"), required("SATARK_TEST_VIEWER_PASSWORD")),
    ]
    if len({email.casefold() for _, email, _ in users}) != 3:
        raise RuntimeError("test_identities_must_use_distinct_emails")
    user_ids = [login(raw_url, api_key, email, password, label) for label, email, password in users]
    if len(set(user_ids)) != 3:
        raise RuntimeError("test_identities_must_resolve_to_distinct_auth_users")

    print("PASS: isolated Supabase project ref matches the configured test project.")
    print("PASS: all three dedicated test identities authenticated successfully.")
    print("PASS: tenant IDs and authenticated user identities are distinct and structurally valid.")
    print("LIMITATION: this is preflight only; tenant membership, RLS, viewer restrictions, approvals, revocation, and executor authorization remain untested.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
