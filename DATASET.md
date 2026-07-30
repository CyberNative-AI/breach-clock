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

## Dataset license and scope

The software in this repository is MIT-licensed under [LICENSE](LICENSE). CyberNative AI LLC dedicates its copyright and database rights, if any, in the selection and arrangement of the factual dataset in [`data/`](data/) to the public domain under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/legalcode).

This CC0 dedication applies only to `data/` and only to the extent CyberNative AI LLC holds those rights. It does not apply to linked or underlying notice PDFs, notice prose, third-party trademarks, or any other third-party material. The CC0 1.0 Universal legal code and disclaimer are available at https://creativecommons.org/publicdomain/zero/1.0/legalcode.
