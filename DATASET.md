# Dataset candidate

## Provenance

The candidate indexes factual fields mechanically extracted from the California Attorney General’s [data breach notice registry](https://oag.ca.gov/privacy/databreach/list) and its CSV export. The registry describes sample notices submitted for incidents affecting more than 500 California residents. The filer may not be the organization that experienced the incident.

Each build writes a local source manifest with source URL, access time, content type, byte count, and SHA-256. `data/coverage.json` is the committed receipt for the build included here. Source PDFs are inputs only: they are not committed, redistributed, or converted into published notice prose.

## Fields

Every row has: `id`, `organization`, `breach_dates`, `reported_date`, `data_exposed`, `remedy_type`, `remedy_provider`, `remedy_duration_months`, `remedy_duration_text`, `enrollment_deadline`, `enrollment_deadline_timezone`, `deadline_status`, `source_report_url`, `source_notice_url`, `source_notice_sha256`, `source_accessed_at`, and `extraction_confidence`.

`deadline_status` is `open`, `expired`, or `unknown`. It is calculated only from an explicit printed deadline and the recorded build timestamp. An ambiguous or absent deadline stays null and `unknown`; the builder does not infer a deadline from a letter date or the protection duration.

## Coverage and limitations

This candidate is partial. See `data/coverage.json` for its source-record denominator, report pages attempted, notice PDFs fetched, and resolved-row numerator. It does not claim complete registry coverage. Deterministic text extraction can miss a scanned notice or an unfamiliar deadline format. The index does not determine enrolment eligibility and must not be used as a substitute for a recipient’s notice.

The included receipt was updated 2026-07-30. To report a correction, write to hello@cybernative.ai.

## Proposed dataset license

The code is MIT under [LICENSE](LICENSE). That code license does not apply to third-party notice PDFs or notice text. If this factual-field dataset is later distributed, the proposed dataset license is CC0 1.0, subject to independent Security review of provenance and licensing before upload or publication.
