# Breach Clock

Breach Clock builds a small, static index of protection offers and printed enrolment deadlines from California Attorney General data-breach notice filings. It is a search aid, not an eligibility decision: a person’s own letter and its activation code determine whether they can enrol.

## Run

Requires Python 3.11+ and `pdftotext` from Poppler. The scripts use only the Python standard library and make no metered API calls.

```sh
python scripts/fetch_registry.py
python scripts/fetch_notices.py --only-id sb24-626307 --max-reports 1
python scripts/extract_offers.py
python scripts/build_index.py
python -m unittest discover -s tests -v
```

The downloaded source inputs and `build/source-manifest.json` are local build inputs; they are intentionally not committed. Notice PDFs and notice prose are never published by this repository.

## Output

`data/offers.jsonl` is the line-oriented index. `data/offers.json` is the browser-ready equivalent. `data/coverage.json` describes the exact build scope and counts. Each row links to the original report and notice, and records the notice hash and access time.

The code in this repository is MIT-licensed. The proposed dataset license is described separately in [DATASET.md](DATASET.md) and remains subject to independent security review before any upload.
