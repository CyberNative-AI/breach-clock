#!/usr/bin/env python3
"""Build the static offer index and an exact deadline-coverage receipt."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path


def read_jsonl(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def absolute_status(value: str, built_at: str) -> str:
    return "open" if date.fromisoformat(value) >= datetime.fromisoformat(built_at.replace("Z", "+00:00")).date() else "expired"


def normalize_deadline(row: dict, built_at: str) -> dict:
    row = dict(row)
    deadline = row.get("enrollment_deadline")
    relative_days = row.get("deadline_days_from_letter")
    if deadline:
        row["deadline_basis"] = "absolute"
        row["deadline_days_from_letter"] = None
        row["deadline_status"] = absolute_status(deadline, built_at)
    elif isinstance(relative_days, int) and relative_days > 0:
        row["deadline_basis"] = "letter_date_relative"
        row["deadline_days_from_letter"] = relative_days
        row["deadline_status"] = "requires_letter_date"
    else:
        row["deadline_basis"] = "unknown"
        row["deadline_days_from_letter"] = None
        row["deadline_status"] = "unknown"
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="data/offers.jsonl")
    parser.add_argument("--baseline", default="data/offers.jsonl")
    parser.add_argument("--notices", default="build/notices/manifest.jsonl")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--built-at", default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    parser.add_argument("--report-pages-attempted", type=int)
    parser.add_argument("--pdfs-fetched", type=int)
    parser.add_argument("--acquisition-failures", type=int)
    args = parser.parse_args()
    baseline = read_jsonl(args.baseline)
    extracted = {row["id"]: row for row in read_jsonl(args.rows)}
    baseline_ids = [row["id"] for row in baseline]
    if len(baseline_ids) != 137 or len(set(baseline_ids)) != 137:
        raise ValueError("the published baseline must contain exactly 137 unique IDs")
    unexpected = set(extracted) - set(baseline_ids)
    if unexpected:
        raise ValueError("extraction includes IDs outside the published baseline")
    rows = [normalize_deadline(extracted.get(row["id"], row), args.built_at) for row in baseline]
    rows.sort(key=lambda row: (row["organization"] or "").casefold())
    notices = read_jsonl(args.notices) if Path(args.notices).exists() else []
    report_pages = args.report_pages_attempted if args.report_pages_attempted is not None else len(notices)
    pdfs_fetched = args.pdfs_fetched if args.pdfs_fetched is not None else sum("pdf_path" in item for item in notices)
    acquisition_failures = args.acquisition_failures if args.acquisition_failures is not None else sum("error" in item for item in notices)
    absolute = sum(row["deadline_basis"] == "absolute" for row in rows)
    relative = sum(row["deadline_basis"] == "letter_date_relative" for row in rows)
    unknown = sum(row["deadline_basis"] == "unknown" for row in rows)
    resolved = absolute + relative
    coverage = {
        "built_at": args.built_at,
        "total_rows": len(rows),
        "source_record_count": len(rows),
        "source_accessed_at": max((row["source_accessed_at"] for row in rows), default=None),
        "report_pages_attempted": report_pages,
        "pdfs_fetched": pdfs_fetched,
        "acquisition_failures": acquisition_failures,
        "rows_with_absolute_deadlines": absolute,
        "rows_with_relative_letter_date_deadlines": relative,
        "resolved_deadline_rule_count": resolved,
        "resolved_deadline_rule_percentage": round(resolved / len(rows) * 100, 2),
        "rows_unknown": unknown,
        "absolute_rows_open": sum(row["deadline_status"] == "open" for row in rows),
        "absolute_rows_expired": sum(row["deadline_status"] == "expired" for row in rows),
        "coverage_complete": len(rows) == 137 and len({row["id"] for row in rows}) == 137,
    }
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "offers.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (out / "offers.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(coverage, sort_keys=True))


if __name__ == "__main__":
    main()
