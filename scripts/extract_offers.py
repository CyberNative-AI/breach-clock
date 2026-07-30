#!/usr/bin/env python3
"""Deterministically extract factual offer fields without retaining notice prose."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

FORBIDDEN_KEYS = {"activation_code", "enrollment_code", "addressee", "address", "phone", "email", "mailing_address"}
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
PROVIDERS = ("Experian IdentityWorks", "Experian", "Equifax", "TransUnion", "Kroll", "IDX", "AllClear", "Cyberscout")
EXPOSURES = ((r"social security", "Social Security number"), (r"driver.?s license", "Driver's license number"), (r"financial account", "Financial account information"), (r"health information", "Health information"), (r"date of birth", "Date of birth"), (r"name", "Name"))


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def text_from_pdf(path: str) -> str:
    result = subprocess.run(["pdftotext", "-layout", path, "-"], check=True, capture_output=True, text=True)
    return result.stdout


def parse_date(value: str) -> str | None:
    value = value.strip().replace(",", "")
    for pattern in ("%B %d %Y", "%b %d %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            pass
    return None


def deadline_from(text: str) -> tuple[str | None, str | None]:
    pattern = rf"(?:enrol(?:l(?:ment)?)?|register|sign\s*up)\b.{{0,100}}?(?:by|before|until)\s+(({MONTHS})\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}/\d{{1,2}}/\d{{4}})"
    matches = list(re.finditer(pattern, text, flags=re.I | re.S))
    parsed = []
    for match in matches:
        iso = parse_date(match.group(1))
        if iso:
            zone = re.search(r"\b(UTC|PST|PDT|EST|EDT|CST|CDT|MST|MDT|Pacific Time|Eastern Time|Central Time|Mountain Time)\b", text[match.end():match.end() + 45], flags=re.I)
            parsed.append((iso, zone.group(1).upper() if zone else None))
    unique = {(item[0], item[1]) for item in parsed}
    return next(iter(unique)) if len(unique) == 1 else (None, None)


def deadline_status(deadline: str | None, built_at: str) -> str:
    if not deadline:
        return "unknown"
    today = datetime.fromisoformat(built_at.replace("Z", "+00:00")).date()
    printed = date.fromisoformat(deadline)
    if printed > today:
        return "open"
    if printed < today:
        return "expired"
    return "unknown"


def extract(record: dict, text: str, built_at: str) -> dict:
    deadline, zone = deadline_from(text)
    provider = next((name for name in PROVIDERS if re.search(re.escape(name), text, flags=re.I)), None)
    duration = re.search(r"\b(\d{1,2})\s*(months?|years?)\b", text, flags=re.I)
    months = None
    duration_text = None
    if duration:
        raw_number, unit = duration.group(1), duration.group(2).lower()
        months = int(raw_number) * (12 if unit.startswith("year") else 1)
        duration_text = f"{raw_number} {unit}"
    exposure_section = re.search(r"(?:what information was involved|information involved).*?(?:what we are doing|what you can do)", text, flags=re.I | re.S)
    lower = exposure_section.group(0).lower() if exposure_section else ""
    exposed = [label for needle, label in EXPOSURES if re.search(needle, lower)]
    remedy_type = "identity protection" if provider else ("credit monitoring" if re.search(r"credit monitoring", text, flags=re.I) else None)
    fields = {
        "id": record["id"], "organization": record.get("organization"), "breach_dates": record.get("breach_dates", []),
        "reported_date": record.get("reported_date"), "data_exposed": exposed, "remedy_type": remedy_type,
        "remedy_provider": provider, "remedy_duration_months": months, "remedy_duration_text": duration_text,
        "enrollment_deadline": deadline, "enrollment_deadline_timezone": zone,
        "deadline_status": deadline_status(deadline, built_at), "source_report_url": record["report_url"],
        "source_notice_url": record["source_notice_url"], "source_notice_sha256": record["source_notice_sha256"],
        "source_accessed_at": record["source_accessed_at"],
    }
    fields["extraction_confidence"] = round((sum(value is not None and value != [] for value in (fields["organization"], provider, months, deadline)) / 4), 2)
    return {key: value for key, value in fields.items() if key not in FORBIDDEN_KEYS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notices", default="build/notices/manifest.jsonl")
    parser.add_argument("--out", default="build/extracted.jsonl")
    parser.add_argument("--built-at", default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    args = parser.parse_args()
    rows, failures = [], 0
    for line in Path(args.notices).read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if "pdf_path" not in record:
            failures += 1
            continue
        try:
            rows.append(extract(record, text_from_pdf(record["pdf_path"]), args.built_at))
        except (OSError, subprocess.CalledProcessError):
            failures += 1
    Path(args.out).write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "extraction_failures": failures, "built_at": args.built_at}, sort_keys=True))


if __name__ == "__main__":
    main()
