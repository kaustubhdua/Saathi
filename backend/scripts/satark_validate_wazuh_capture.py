#!/usr/bin/env python3
"""Validate a captured Wazuh alerts.jsonl file without a running Wazuh server.

This validates structure, stable source identifiers, duplicate IDs, and hashes.
It cannot prove that an input was captured from a live Wazuh deployment; that
requires a separately retained capture manifest and live-session evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def get_path(record: dict[str, Any], *path: str) -> Any:
    value: Any = record
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def validate(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    hashes: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    records = 0

    with path.open("r", encoding="utf-8") as stream:
        for line_no, raw in enumerate(stream, start=1):
            if not raw.strip():
                continue
            records += 1
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append({"line": line_no, "error": f"invalid JSON: {exc.msg}"})
                continue
            if not isinstance(record, dict):
                errors.append({"line": line_no, "error": "record must be a JSON object"})
                continue

            # Wazuh alert records commonly expose these fields. Do not fabricate
            # missing identifiers or silently substitute a locally generated ID.
            event_id = record.get("id")
            timestamp = record.get("timestamp")
            rule_id = get_path(record, "rule", "id")
            agent_id = get_path(record, "agent", "id")
            missing = [
                name for name, value in (
                    ("id", event_id),
                    ("timestamp", timestamp),
                    ("rule.id", rule_id),
                    ("agent.id", agent_id),
                ) if value is None or str(value).strip() == ""
            ]
            if missing:
                errors.append({
                    "line": line_no,
                    "error": "missing required source fields: " + ", ".join(missing),
                })
                continue

            source_id = str(event_id)
            if source_id in seen:
                errors.append({
                    "line": line_no,
                    "error": f"duplicate Wazuh source id {source_id!r}; first seen on line {seen[source_id]}",
                })
            else:
                seen[source_id] = line_no

            hashes.append({
                "line": line_no,
                "source_id": source_id,
                "timestamp": str(timestamp),
                "agent_id": str(agent_id),
                "rule_id": str(rule_id),
                "record_sha256": hashlib.sha256(canonical_json(record)).hexdigest(),
            })

    summary = {
        "input_file": path.name,
        "records_seen": records,
        "records_hashed": len(hashes),
        "unique_source_ids": len(seen),
        "valid": records > 0 and not errors and len(hashes) == records,
        "errors": errors,
        "important_limit": (
            "Schema/hash validation is not proof of live capture, successful SATARK "
            "ingestion, tenant isolation, or response execution."
        ),
    }
    return summary, hashes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("alerts_jsonl", type=Path, help="Captured Wazuh alert records, one JSON object per line")
    parser.add_argument("--report", type=Path, help="Write a JSON report (default: stdout)")
    args = parser.parse_args()

    try:
        summary, hashes = validate(args.alerts_jsonl)
    except OSError as exc:
        print(f"ERROR: cannot read input: {exc}", file=sys.stderr)
        return 2

    report = {"summary": summary, "records": hashes}
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        try:
            args.report.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: cannot write report: {exc}", file=sys.stderr)
            return 2
    else:
        print(rendered, end="")
    return 0 if summary["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
