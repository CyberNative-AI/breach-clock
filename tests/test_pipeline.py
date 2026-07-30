import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extract = load("extract_offers")


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


if __name__ == "__main__":
    unittest.main()
