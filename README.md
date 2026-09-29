# Breach Clock: protection offers and enrolment deadlines from California breach notices

The 2026-07-30 baseline indexes 137 notices filed with the California Attorney General. 56 of them (40.9%) carry a deadline rule we could resolve from the notice text: 20 fixed dates and 36 counted from the date on the recipient's letter. Each row links to its original report and notice, with the notice hash and access time.

Search it in the browser: https://cybernative.ai/products/breach-clock/

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

`data/offers.jsonl` is the line-oriented index. `data/offers.json` is the browser-ready equivalent. `data/coverage.json` describes the exact build scope and counts. The baseline records 137 report-page attempts, 136 fetched PDFs and one failed acquisition.

## Limits

Breach Clock is a search aid, not an eligibility decision: a person's own letter and its activation code determine whether they can enrol. A relative deadline needs the visitor's own letter date; the dataset never invents that date or a deadline derived from it, and never infers one from a protection duration or mailing date. 81 of the 137 rows carry no resolved rule, and deterministic text extraction can miss a scanned notice or an unfamiliar deadline format.

## Licence

The software is MIT-licensed. CyberNative AI LLC dedicates only its rights, if any, in the selection and arrangement of `data/` under CC0 1.0 Universal; linked or underlying notices, notice prose, third-party trademarks, and other third-party material are excluded. [DATASET.md](DATASET.md) governs the exact scope.

## Contact

Questions, corrections or bug reports: [hello@cybernative.ai](mailto:hello@cybernative.ai).
