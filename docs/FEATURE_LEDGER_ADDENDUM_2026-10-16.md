# Saathi Feature Ledger Addendum — 2026-10-16

## Weather provenance sprint

- Candidate branch: `fix/weather-observation-provenance-2026-10-16`.
- Open-Meteo now requires a provider observation timestamp and valid IANA timezone, normalizes the timestamp to UTC, and stores it separately from retrieval time.
- Observations older than three hours or more than five minutes in the future are withheld with explicit stale/future status. Missing or malformed observation times and invalid hourly probabilities fail closed.
- Missing rain probabilities are never converted to `0%`; tomorrow-specific requests do not reuse a next-24-hour probability when tomorrow's value is absent.
- The existing dashboard source note shows the provider observation timestamp and freshness status, while the retrieval timestamp remains separately visible.
- Regression tests cover timezone normalization, stale observations, missing timestamps, invalid probabilities, missing tomorrow values and freshness classification.
- Exact-head CI, live provider behavior, and production deployment remain unverified. No deployment or database change was attempted.
