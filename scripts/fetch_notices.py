#!/usr/bin/env python3
"""Fetch report pages and linked PDFs as local, uncommitted build inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "BreachClock/0.1 (+https://cybernative.ai)"})
    with urlopen(request, timeout=60) as response:
        return response.read(), response.headers.get_content_type()


def receipt(url: str, payload: bytes, content_type: str, accessed_at: str) -> dict:
    return {"url": url, "accessed_at": accessed_at, "size": len(payload), "content_type": content_type, "sha256": hashlib.sha256(payload).hexdigest()}


def notice_url(report_html: str) -> str | None:
    match = re.search(r'href="(https://oag\.ca\.gov/system/files/[^"]+\.pdf[^"]*)"', report_html, flags=re.I)
    return match.group(1) if match else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", default="build/reports.jsonl")
    parser.add_argument("--out-dir", default="build/notices")
    parser.add_argument("--manifest", default="build/source-manifest.json")
    parser.add_argument("--only-id")
    parser.add_argument("--max-reports", type=int, default=25)
    args = parser.parse_args()
    reports = [json.loads(line) for line in Path(args.reports).read_text(encoding="utf-8").splitlines() if line]
    if args.only_id:
        reports = [report for report in reports if report["id"] == args.only_id]
    reports = reports[:args.max_reports]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    output = []
    seen = set()
    for report in reports:
        accessed_at = utc_now()
        try:
            page, page_type = fetch(report["report_url"])
            manifest.append(receipt(report["report_url"], page, page_type, accessed_at))
            url = notice_url(page.decode("utf-8", errors="replace"))
            if not url:
                continue
            pdf, pdf_type = fetch(url)
            item = receipt(url, pdf, pdf_type, accessed_at)
            manifest.append(item)
            identity = (report["report_url"], item["sha256"])
            if identity in seen:
                continue
            seen.add(identity)
            path = out_dir / f'{report["id"]}.pdf'
            path.write_bytes(pdf)
            output.append({**report, "source_notice_url": url, "source_notice_sha256": item["sha256"], "source_accessed_at": accessed_at, "pdf_path": str(path)})
        except Exception as exc:
            output.append({**report, "error": type(exc).__name__})
    with (out_dir / "manifest.jsonl").open("w", encoding="utf-8") as handle:
        for item in output:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report_pages_attempted": len(reports), "notice_rows": len(output), "pdfs_fetched": sum("pdf_path" in item for item in output)}, sort_keys=True))


if __name__ == "__main__":
    main()
