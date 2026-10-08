"""Report/input safeguards: uploaded content cannot establish authority or real mode."""

import copy
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from lab.reports import (
    MAX_UPLOAD_BYTES, SnapshotError, build_daily_report, empty_snapshot,
    normalize_snapshot, parse_snapshot, safe_text,
)


class SnapshotTests(unittest.TestCase):
    def test_empty_snapshot_is_paper_and_has_no_fabricated_prices(self):
        snapshot = parse_snapshot(json.dumps(empty_snapshot()))
        self.assertEqual(snapshot["mode"], "paper")
        self.assertEqual(snapshot["opportunities"], [])
        self.assertEqual(snapshot["trades"], [])

    def test_real_mode_is_rejected_at_any_level(self):
        for change in ({"mode": "real"}, {"trades": [{"mode": "real"}]}):
            value = empty_snapshot()
            value.update(change)
            with self.subTest(change=change), self.assertRaises(SnapshotError):
                normalize_snapshot(value)

    def test_duplicate_keys_nonfinite_numbers_and_broken_json_are_rejected(self):
        for raw in (b'{"mode":"paper","mode":"real","schema_version":1}',
                    b'{"schema_version":1,"mode":"paper","x":NaN}',
                    b'{"schema_version":1,"mode":"paper","x":1e1000}', b"{", b"\xff"):
            with self.subTest(raw=raw), self.assertRaises(SnapshotError):
                parse_snapshot(raw)

    def test_upload_size_structure_and_collection_limits(self):
        with self.assertRaises(SnapshotError):
            parse_snapshot(b" " * (MAX_UPLOAD_BYTES + 1))
        value = empty_snapshot()
        value["trades"] = [{}] * 1001
        with self.assertRaises(SnapshotError):
            normalize_snapshot(value)
        value = empty_snapshot()
        value["x"] = nested = {}
        for _ in range(13):
            nested["x"] = {}
            nested = nested["x"]
        with self.assertRaises(SnapshotError):
            normalize_snapshot(value)

    def test_secret_fields_and_malformed_records_are_rejected_without_echo(self):
        value = empty_snapshot()
        value["account"] = {"api_key": "PRIVATEVALUE"}
        with self.assertRaises(SnapshotError) as ctx:
            normalize_snapshot(value)
        self.assertNotIn("PRIVATEVALUE", str(ctx.exception))
        value = empty_snapshot()
        value["trades"] = ["not a record"]
        with self.assertRaises(SnapshotError):
            normalize_snapshot(value)

    def test_malicious_text_is_not_executable_or_a_markdown_link(self):
        payload = '<script>fetch("https://bad.invalid")</script>\n[click](https://bad.invalid)'
        rendered = safe_text(payload)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("[click]", rendered)
        self.assertNotIn("\n", rendered)
        value = empty_snapshot()
        value["market_context"] = payload
        self.assertEqual(normalize_snapshot(value)["market_context"], payload)

    def test_input_is_copied(self):
        value = empty_snapshot()
        snapshot = normalize_snapshot(value)
        snapshot["account"]["capital_initial_clp"] = 10
        self.assertEqual(value["account"], {})


class ReportTests(unittest.TestCase):
    now = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)

    def test_empty_report_declines_and_has_no_real_order_authority(self):
        report = build_daily_report(empty_snapshot(), self.now)
        self.assertEqual(report["status"], "NO_OPERAR")
        self.assertFalse(report["ballot"]["real_order_authorized"])
        self.assertIn("No existe una oportunidad confiable evaluable", report["markdown"])

    def test_naive_evaluation_time_is_rejected(self):
        with self.assertRaises(SnapshotError):
            build_daily_report(empty_snapshot(), datetime(2026, 10, 8))

    def test_limit_three_opportunities_and_strip_claimed_authentication(self):
        snapshot = empty_snapshot()
        snapshot["opportunities"] = [{"symbol": f"TEST{i}"} for i in range(5)]
        snapshot["account"] = {"strategy_approved": True}
        snapshot["governance"] = {
            "proposal": {"trusted_collector": True, "integrity_verified": True,
                         "evidence_complete": True, "invitations_verified": True,
                         "access_verified": True}, "votes": [],
        }
        original = copy.deepcopy(snapshot)
        with patch("lab.risk.evaluate_risk", return_value={"status": "NO_OPERAR", "reasons": []}) as risk, \
             patch("lab.governance.evaluate_ballot", return_value={"status": "HUMAN_REVIEW", "real_order_authorized": False}) as ballot:
            report = build_daily_report(snapshot, self.now)
        self.assertEqual(risk.call_count, 3)
        self.assertFalse(risk.call_args.args[1]["strategy_approved"])
        self.assertEqual(len(report["opportunities"]), 3)
        self.assertTrue(all(not ballot.call_args.args[0][flag] for flag in (
            "trusted_collector", "integrity_verified", "evidence_complete", "invitations_verified", "access_verified")))
        self.assertEqual(snapshot, original)

    def test_demo_always_identified_as_synthetic(self):
        snapshot = empty_snapshot()
        snapshot["synthetic"] = True
        report = build_daily_report(snapshot, self.now)
        self.assertIn("Datos sintéticos de demostración", report["markdown"])
        self.assertIn("SIMULACIÓN", report["markdown"])


if __name__ == "__main__":
    unittest.main()
