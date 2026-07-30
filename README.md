# Breach Clock

Breach Clock builds a small, static index of protection offers and printed enrolment deadlines from California Attorney General data-breach notice filings. It is a search aid, not an eligibility decision: a person’s own letter and its activation code determine whether they can enrol.

## Run

Requires Python 3.11+ and `pdftotext` from Poppler. The scripts use only the Python standard library and make no metered API calls.

```sh
python scripts/fetch_registry.py
python scripts/fetch_notices.py
python scripts/extract_offers.py
python scripts/build_index.py
python -m unittest discover -s tests -v
```

`build_index.py` consumes `build/extracted.jsonl` by default, produced by the immediately preceding extraction command. The downloaded source inputs and `build/source-manifest.json` are local build inputs; they are intentionally not committed. Notice PDFs and notice prose are never published by this repository.

## Output

`data/offers.jsonl` is the line-oriented index. `data/offers.json` is the browser-ready equivalent. `data/coverage.json` describes the exact build scope and counts. Each row links to the original report and notice, and records the notice hash and access time. Relative deadline rows require a visitor-provided letter date; the static dataset never fabricates that date or a derived deadline.

The software is MIT-licensed. CyberNative AI LLC dedicates only its rights, if any, in the selection and arrangement of `data/` under CC0 1.0 Universal; linked or underlying notices, notice prose, third-party trademarks, and other third-party material are excluded. [DATASET.md](DATASET.md) governs the exact scope.
