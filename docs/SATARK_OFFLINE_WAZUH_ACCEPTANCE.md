# SATARK: offline-first Wazuh acceptance workflow

This workflow avoids keeping a machine online continuously. It separates offline
repeatability from the one-time live acceptance session required to claim real
Wazuh integration.

## What can be done offline

- Develop and run unit tests for parsing, source-ID preservation, deduplication,
  canonical record hashing, and evidence-bundle handling.
- Validate a captured alert export with
  `python backend/scripts/satark_validate_wazuh_capture.py alerts.jsonl --report capture-report.json`.
- Re-run deterministic tests against a retained, access-controlled capture.
- Review the output report and compare record hashes after copying or archiving.

The validator expects one JSON object per line and checks that each record has
Wazuh source fields `id`, `timestamp`, `rule.id`, and `agent.id`. It rejects
missing required fields and duplicate source IDs. It hashes each full JSON
record after canonical JSON serialization. It does not mutate the source file.

## One-time live capture required for a real-integration claim

1. Start an isolated Wazuh lab and a test endpoint for a bounded test window.
2. Record the Wazuh version, lab identifier, UTC start/end time, and operator.
   Keep credentials and private endpoint details out of the manifest.
3. Generate benign, authorized test events on that endpoint and confirm that
   Wazuh itself produced the corresponding alerts.
4. Export the actual alert records from Wazuh. Do not hand-author alert objects
   and label them as live telemetry.
5. Run the offline validator against that export and preserve its JSON report.
6. Send the captured alerts through SATARK's real ingestion endpoint in the
   isolated test environment. Record request IDs, responses, persisted source
   IDs, tenant IDs, and evidence digests without exposing tokens or secrets.
7. Query persisted records independently and verify source-ID preservation,
   deduplication, tenant scoping, and evidence digest consistency.
8. Tear down the lab after logs and test evidence are safely retained.

## Acceptance status vocabulary

- **Offline validator passed:** input schema, required source fields, duplicate
  source IDs, and deterministic hashes passed.
- **Live Wazuh capture verified:** a bounded live session generated alerts and
  the capture is linked to a sanitized session manifest.
- **SATARK ingestion verified:** live-captured alerts were submitted to the
  deployed test ingestion route and independently found in persistence.
- **End-to-end acceptance passed:** ingestion, tenant isolation, provenance,
  evidence integrity, and required audit checks all passed.

Do not infer a later status from an earlier one. The validator alone cannot
prove that a capture came from Wazuh, that SATARK received it, or that a response
was executed. Replayed captures must be labeled as replayed test inputs.

## Safety and cost controls

- Use an isolated test project and non-production tenant IDs.
- Never place service-role keys, passwords, bearer tokens, or private alert data
  in committed fixtures, reports, screenshots, or CI logs.
- Do not expose Wazuh manager/indexer ports publicly; restrict access to the
  lab network and use strong credentials.
- Use only benign events and explicitly authorized endpoints.
- Stop the VM/containers after the live test. Confirm that persistent disks and
  other billable resources are also handled according to the provider's billing
  model.
- Keep response execution disabled until the authenticated approval lifecycle,
  atomic approval consumption, and harmless lab action are separately verified.
