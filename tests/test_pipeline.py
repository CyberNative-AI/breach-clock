import importlib.util
from http.client import IncompleteRead
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract = load("extract_offers")
transport = load("fetch_registry")


class OfferExtractionTests(unittest.TestCase):
    def record(self, identifier="sb24-626307", organization="Wilmer Cutler Pickering Hale and Dorr LLP"):
        return {"id": identifier, "organization": organization, "breach_dates": ["2026-05-08"], "reported_date": "2026-07-10", "report_url": f"https://oag.ca.gov/ecrime/databreach/reports/{identifier}", "source_notice_url": "https://oag.ca.gov/system/files/example.pdf", "source_notice_sha256": "a" * 64, "source_accessed_at": "2026-07-30T00:00:00Z"}

    def test_verified_fixture_values(self):
        text = "Wilmer Cutler Pickering Hale and Dorr LLP offers Experian IdentityWorks for 24 months. Name and Social Security number were involved. You must enroll by October 30, 2026 at 23:59 UTC."
        row = extract.extract(self.record(), text, "2026-07-30T00:00:00Z")
        self.assertEqual(row["organization"], "Wilmer Cutler Pickering Hale and Dorr LLP")
        self.assertEqual(row["breach_dates"], ["2026-05-08"])
        self.assertEqual(row["remedy_provider"], "Experian IdentityWorks")
        self.assertEqual(row["remedy_duration_months"], 24)
        self.assertEqual(row["enrollment_deadline"], "2026-10-30")
        self.assertEqual(row["enrollment_deadline_timezone"], "UTC")
        self.assertEqual(row["deadline_status"], "open")

    def test_ambiguous_deadlines_are_unknown(self):
        row = extract.extract(self.record(), "Enroll by October 30, 2026. Register before November 1, 2026.", "2026-07-30T00:00:00Z")
        self.assertIsNone(row["enrollment_deadline"])
        self.assertEqual(row["deadline_status"], "unknown")

    def test_missing_remedy_stays_null(self):
        row = extract.extract(self.record(), "Enroll by October 30, 2026 UTC.", "2026-07-30T00:00:00Z")
        self.assertIsNone(row["remedy_type"])
        self.assertIsNone(row["remedy_provider"])
        self.assertIsNone(row["remedy_duration_months"])

    def test_multiple_breach_dates_are_preserved(self):
        record = self.record()
        record["breach_dates"] = ["2026-05-08", "2026-05-09"]
        self.assertEqual(extract.extract(record, "", "2026-07-30T00:00:00Z")["breach_dates"], ["2026-05-08", "2026-05-09"])

    def test_repeated_organizations_are_distinct_source_rows(self):
        first = extract.extract(self.record("sb24-1", "Example Inc."), "", "2026-07-30T00:00:00Z")
        second = extract.extract(self.record("sb24-2", "Example Inc."), "", "2026-07-30T00:00:00Z")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["organization"], second["organization"])

    def test_explicit_timezone_and_person_fields_are_safe(self):
        row = extract.extract(self.record(), "Enroll before 10/30/2026 PDT. Morgan Example lives at 10 Example Street.", "2026-07-30T00:00:00Z")
        self.assertEqual(row["enrollment_deadline_timezone"], "PDT")
        self.assertFalse({"activation_code", "enrollment_code", "addressee", "address", "phone", "email", "mailing_address"} & set(row))
        self.assertNotIn("Morgan Example", json.dumps(row))
        self.assertNotIn("10 Example Street", json.dumps(row))


    def test_same_day_explicit_deadline_is_open(self):
        row = extract.extract(self.record(), "Enroll by July 30, 2026 UTC.", "2026-07-30T18:00:00Z")
        self.assertEqual(row["deadline_status"], "open")


    def test_relative_letter_date_deadline(self):
        row = extract.extract(self.record(), "Register within 90 days from the date of this letter.", "2026-07-30T00:00:00Z")
        self.assertIsNone(row["enrollment_deadline"])
        self.assertEqual(row["deadline_basis"], "letter_date_relative")
        self.assertEqual(row["deadline_days_from_letter"], 90)
        self.assertEqual(row["deadline_status"], "requires_letter_date")

    def test_spelled_relative_deadline_requires_matching_numeric_value(self):
        self.assertEqual(extract.relative_deadline_from("Sign up within ninety (90) days of the date of your letter."), 90)
        self.assertIsNone(extract.relative_deadline_from("Sign up within ninety (60) days of the date of your letter."))

    def test_relative_deadline_rejects_wrong_actions_anchors_and_conflicts(self):
        self.assertIsNone(extract.relative_deadline_from("Monitoring lasts 90 days from the date of this letter."))
        self.assertIsNone(extract.relative_deadline_from("Enroll within 90 days from the breach date."))
        self.assertIsNone(extract.relative_deadline_from("Register within 60 days from the date of this letter. Enroll within 90 days from the date of this letter."))

    def test_absolute_and_relative_windows_are_conservatively_unresolved(self):
        row = extract.extract(self.record(), "Enroll by October 30, 2026. Register within 90 days from the date of this letter.", "2026-07-30T00:00:00Z")
        self.assertEqual(row["deadline_basis"], "unknown")
        self.assertEqual(row["deadline_status"], "unknown")


    def test_static_artifacts_keep_the_137_row_provenance_contract(self):
        rows = json.loads((ROOT / "data" / "offers.json").read_text(encoding="utf-8"))
        coverage = json.loads((ROOT / "data" / "coverage.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 137)
        self.assertEqual(len({row["id"] for row in rows}), 137)
        self.assertEqual(coverage["total_rows"], 137)
        self.assertEqual(coverage["resolved_deadline_rule_count"], coverage["rows_with_absolute_deadlines"] + coverage["rows_with_relative_letter_date_deadlines"])
        retained = next(row for row in rows if row["id"] == "sb24-624003")
        self.assertEqual(retained["enrollment_deadline"], "2026-08-31")
        self.assertEqual(retained["deadline_basis"], "absolute")
        self.assertEqual(retained["deadline_status"], "open")
        for row in rows:
            self.assertIn(row["deadline_basis"], {"absolute", "letter_date_relative", "unknown"})
            self.assertTrue(row["source_report_url"].startswith("https://oag.ca.gov/"))
            self.assertTrue(row["source_notice_url"].startswith("https://oag.ca.gov/"))
            if row["deadline_basis"] == "letter_date_relative":
                self.assertIsNone(row["enrollment_deadline"])
                self.assertGreater(row["deadline_days_from_letter"], 0)
                self.assertEqual(row["deadline_status"], "requires_letter_date")


    def test_documented_default_build_uses_extracted_rows_and_manifest_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "build" / "notices").mkdir(parents=True)
            baseline, extracted_rows, notices = [], [], []
            for index in range(137):
                identifier = f"sb24-{index:06d}"
                row = {
                    "id": identifier, "organization": f"Organization {index}",
                    "enrollment_deadline": None, "enrollment_deadline_timezone": None,
                    "deadline_basis": "unknown", "deadline_days_from_letter": None,
                    "deadline_status": "unknown", "source_report_url": "https://oag.ca.gov/report",
                    "source_notice_url": "https://oag.ca.gov/notice.pdf",
                    "source_notice_sha256": "a" * 64, "source_accessed_at": "2026-07-30T00:00:00Z",
                }
                if index == 0:
                    row.update({"id": "sb24-624003", "enrollment_deadline": "2026-08-31", "deadline_basis": "absolute", "deadline_status": "open"})
                baseline.append(row)
                extracted = dict(row)
                extracted.update({"enrollment_deadline": None, "enrollment_deadline_timezone": None, "deadline_basis": "unknown", "deadline_status": "unknown", "source_accessed_at": "2026-07-31T00:00:00Z"})
                if index == 1:
                    extracted.update({"deadline_basis": "letter_date_relative", "deadline_days_from_letter": 90, "deadline_status": "requires_letter_date"})
                extracted_rows.append(extracted)
                notice = dict(row)
                if index < 136:
                    notice["pdf_path"] = f"build/notices/{identifier}.pdf"
                else:
                    notice["error"] = "HTTPError"
                notices.append(notice)
            for path, rows_to_write in ((root / "data" / "offers.jsonl", baseline), (root / "build" / "extracted.jsonl", extracted_rows), (root / "build" / "notices" / "manifest.jsonl", notices)):
                path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows_to_write), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts" / "build_index.py"), "--built-at", "2026-07-30T00:00:00Z"], cwd=root, check=True, capture_output=True, text=True)
            coverage = json.loads((root / "data" / "coverage.json").read_text(encoding="utf-8"))
            rebuilt = json.loads((root / "data" / "offers.json").read_text(encoding="utf-8"))
            retained = next(row for row in rebuilt if row["id"] == "sb24-624003")
            self.assertEqual((coverage["pdfs_fetched"], coverage["acquisition_failures"]), (136, 1))
            self.assertEqual((coverage["rows_with_absolute_deadlines"], coverage["rows_with_relative_letter_date_deadlines"]), (1, 1))
            self.assertEqual(retained["enrollment_deadline"], "2026-08-31")
            self.assertEqual(retained["source_accessed_at"], "2026-07-31T00:00:00Z")


class TransportTests(unittest.TestCase):
    def test_incomplete_read_retries_once_then_records_success(self):
        calls = []

        class Response:
            headers = type("Headers", (), {"get_content_type": lambda self: "application/pdf"})()

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                if isinstance(self.payload, Exception):
                    raise self.payload
                return self.payload

        payloads = [IncompleteRead(b"partial", 12), b"complete notice"]

        def opener(_request, timeout):
            calls.append(timeout)
            return Response(payloads.pop(0))

        body, content_type, attempts = transport.fetch("https://example.test/notice.pdf", opener=opener, pause=lambda _: None)
        self.assertEqual(body, b"complete notice")
        self.assertEqual(content_type, "application/pdf")
        self.assertEqual(attempts, 2)
        self.assertEqual(calls, [60, 60])


if __name__ == "__main__":
    unittest.main()
