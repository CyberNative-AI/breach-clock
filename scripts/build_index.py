#!/usr/bin/env python3
"""Build publication JSON and a coverage receipt from extracted factual rows."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="build/extracted.jsonl")
    parser.add_argument("--reports", default="build/reports.jsonl")
    parser.add_argument("--notices", default="build/notices/manifest.jsonl")
    parser.add_argument("--out-dir", default="data")
    parser.add_argument("--built-at", default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    parser.add_argument("--report-pages-attempted", type=int)
    parser.add_argument("--pdfs-fetched", type=int)
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.rows).read_text(encoding="utf-8").splitlines() if line]
    reports = [line for line in Path(args.reports).read_text(encoding="utf-8").splitlines() if line]
    notices = [json.loads(line) for line in Path(args.notices).read_text(encoding="utf-8").splitlines() if line]
    rows.sort(key=lambda row: (row["organization"] or "").casefold())
    counts = Counter(row["deadline_status"] for row in rows)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "offers.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (out / "offers.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    coverage = {
        "built_at": args.built_at, "source_record_count": len(reports), "report_pages_attempted": args.report_pages_attempted if args.report_pages_attempted is not None else len(notices),
        "pdfs_fetched": args.pdfs_fetched if args.pdfs_fetched is not None else sum("pdf_path" in row for row in notices), "extraction_failures": sum("error" in row for row in notices) + sum("pdf_path" not in row for row in notices),
        "resolved_record_count": len(rows), "rows_with_any_remedy": sum(bool(row["remedy_type"]) for row in rows),
        "rows_with_explicit_deadline": sum(bool(row["enrollment_deadline"]) for row in rows), "rows_open": counts["open"],
        "rows_expired": counts["expired"], "rows_unknown": counts["unknown"], "coverage_complete": len(rows) == len(reports),
    }
    (out / "coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(coverage, sort_keys=True))


if __name__ == "__main__":
    main()
