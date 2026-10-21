"""Unit tests for the offline Wazuh capture validator."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "satark_validate_wazuh_capture.py"
SPEC = importlib.util.spec_from_file_location("satark_wazuh_validator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def alert(source_id="evt-001"):
    return {
        "id": source_id,
        "timestamp": "2026-10-22T00:00:00.000+0000",
        "agent": {"id": "007", "name": "isolated-test-endpoint"},
        "rule": {"id": "5710", "level": 5},
        "full_log": "Authorized benign test event",
    }


class WazuhCaptureValidatorTests(unittest.TestCase):
    def run_records(self, records):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        path = Path(handle.name)
        try:
            with handle:
                for record in records:
                    handle.write(json.dumps(record) + "\n")
            return MODULE.validate(path)
        finally:
            path.unlink(missing_ok=True)

    def test_valid_record_is_hashed_and_source_id_preserved(self):
        summary, rows = self.run_records([alert()])
        self.assertTrue(summary["valid"])
        self.assertEqual(rows[0]["source_id"], "evt-001")
        self.assertEqual(len(rows[0]["record_sha256"]), 64)

    def test_duplicate_source_id_fails_closed(self):
        summary, _ = self.run_records([alert("same"), alert("same")])
        self.assertFalse(summary["valid"])
        self.assertTrue(any("duplicate Wazuh source id" in e["error"] for e in summary["errors"]))

    def test_missing_source_id_fields_fail(self):
        bad = alert()
        del bad["agent"]["id"]
        summary, _ = self.run_records([bad])
        self.assertFalse(summary["valid"])
        self.assertTrue(any("agent.id" in e["error"] for e in summary["errors"]))

    def test_invalid_json_fails(self):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        path = Path(handle.name)
        try:
            with handle:
                handle.write("{not-json}\n")
            summary, _ = MODULE.validate(path)
            self.assertFalse(summary["valid"])
            self.assertIn("invalid JSON", summary["errors"][0]["error"])
        finally:
            path.unlink(missing_ok=True)

    def test_empty_capture_fails(self):
        summary, rows = self.run_records([])
        self.assertFalse(summary["valid"])
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
