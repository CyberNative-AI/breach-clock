#!/usr/bin/env python3
"""Fetch the official registry and make a local, hashed source receipt."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

REGISTRY_URL = "https://oag.ca.gov/privacy/databreach/list"
CSV_URL = "https://oag.ca.gov/privacy/databreach/list-export"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "BreachClock/0.1 (+https://cybernative.ai)"})
    with urlopen(request, timeout=60) as response:
        return response.read(), response.headers.get_content_type()


def receipt(url: str, payload: bytes, content_type: str, accessed_at: str) -> dict:
    return {"url": url, "accessed_at": accessed_at, "size": len(payload), "content_type": content_type, "sha256": hashlib.sha256(payload).hexdigest()}


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def iso_date(value: str) -> str | None:
    value = value.strip()
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", value)
    if not match:
        return None
    return f"{match.group(3)}-{match.group(1)}-{match.group(2)}"


def parse_reports(html: str) -> list[dict]:
    reports = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I):
        link = re.search(r'href="(https://oag\.ca\.gov/ecrime/databreach/reports/(sb24-\d+))"[^>]*>(.*?)</a>', row, flags=re.S | re.I)
        if not link:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S | re.I)
        dates = [iso_date(value) for value in re.findall(r">([^<]*\d{2}/\d{2}/\d{4}[^<]*)<", row)]
        reports.append({
            "id": link.group(2), "report_url": link.group(1), "organization": plain(link.group(3)),
            "breach_dates": [date for date in dates[:-1] if date], "reported_date": dates[-1] if dates else None,
        })
    return reports


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build")
    args = parser.parse_args()
    build = Path(args.build_dir)
    build.mkdir(parents=True, exist_ok=True)
    accessed_at = utc_now()
    csv_bytes, csv_type = fetch(CSV_URL)
    html_bytes, html_type = fetch(REGISTRY_URL)
    (build / "registry.csv").write_bytes(csv_bytes)
    (build / "registry.html").write_bytes(html_bytes)
    reports = parse_reports(html_bytes.decode("utf-8", errors="replace"))
    with (build / "reports.jsonl").open("w", encoding="utf-8") as handle:
        for report in reports:
            handle.write(json.dumps(report, sort_keys=True) + "\n")
    csv_rows = list(csv.DictReader(csv_bytes.decode("utf-8-sig").splitlines()))
    manifest = [receipt(CSV_URL, csv_bytes, csv_type, accessed_at), receipt(REGISTRY_URL, html_bytes, html_type, accessed_at)]
    (build / "source-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"csv_records": len(csv_rows), "report_links": len(reports), "manifest": str(build / "source-manifest.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
