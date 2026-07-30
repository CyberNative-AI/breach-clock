#!/usr/bin/env python3
"""Fetch report pages and linked PDFs as local, uncommitted build inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from extract_offers import deadline_from, text_from_pdf
from fetch_registry import fetch


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def receipt(url: str, payload: bytes, content_type: str, accessed_at: str, attempts: int) -> dict:
    return {"url": url, "accessed_at": accessed_at, "size": len(payload), "content_type": content_type, "sha256": hashlib.sha256(payload).hexdigest(), "acquisition_attempts": attempts}


def notice_url(report_html: str) -> str | None:
    match = re.search(r'href="(https://oag\.ca\.gov/system/files/[^"]+\.pdf[^"]*)"', report_html, flags=re.I)
    return match.group(1) if match else None


def baseline_records(path: str, only_id: str | None) -> list[dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("baseline contains duplicate row IDs")
    if only_id:
        rows = [row for row in rows if row["id"] == only_id]
        if not rows:
            raise ValueError("requested baseline ID was not found")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="data/offers.jsonl")
    parser.add_argument("--out-dir", default="build/notices")
    parser.add_argument("--manifest", default="build/source-manifest.json")
    parser.add_argument("--only-id")
    parser.add_argument("--expected-count", type=int, default=137)
    args = parser.parse_args()
    records = baseline_records(args.baseline, args.only_id)
    if not args.only_id and len(records) != args.expected_count:
        raise ValueError(f"baseline count {len(records)} does not match expected {args.expected_count}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest)
    source_manifest = []
    output, failures, changes, fetched = [], 0, 0, 0
    for record in records:
        accessed_at = utc_now()
        item = dict(record)
        expected_url = record["source_notice_url"]
        expected_sha = record["source_notice_sha256"]
        try:
            page, page_type, page_attempts = fetch(record["source_report_url"])
            source_manifest.append(receipt(record["source_report_url"], page, page_type, accessed_at, page_attempts))
            discovered_url = notice_url(page.decode("utf-8", errors="replace"))
            if discovered_url != expected_url:
                item.update({"error": "source_url_changed", "observed_notice_url": discovered_url})
                changes += 1
            else:
                pdf, pdf_type, pdf_attempts = fetch(expected_url)
                observed = receipt(expected_url, pdf, pdf_type, accessed_at, pdf_attempts)
                source_manifest.append(observed)
                if observed["sha256"] != expected_sha:
                    item.update({"error": "source_sha256_changed", "observed_notice_sha256": observed["sha256"]})
                    changes += 1
                else:
                    path = out_dir / f"{record['id']}.pdf"
                    path.write_bytes(pdf)
                    item["pdf_path"] = str(path)
                    fetched += 1
        except Exception as exc:
            item["error"] = type(exc).__name__
            failures += 1
        output.append(item)
    if len({item["id"] for item in output}) != len(records):
        raise AssertionError("acquisition changed the baseline ID set")
    with (out_dir / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for item in output:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    manifest_path.write_text(json.dumps(source_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"baseline_rows": len(records), "notice_rows": len(output), "pdfs_fetched": fetched, "acquisition_failures": failures, "source_changes": changes}, sort_keys=True))


if __name__ == "__main__":
    main()
