> Historical plan: superseded by the current OCR-to-database scope.

# Implementation approach and review decisions

Status: Planning only. Launch date: TBD (confirmed). These are proposed work packages; no application code, migrations, infrastructure or source-data changes have been made.

## Recommended approach

Build an evidence-first import pipeline with human review, a single authoritative consent registry, and end-to-end withdrawal enforcement. Keep OCR replaceable: choose it on real forms using field and consent-decision accuracy rather than brand or text-recognition scores alone.

Separate document duplicates, identity matches and repeated consent events. They require different evidence and different review actions. Keep historical evidence even when multiple imports refer to the same canonical decision, subject to retention policy.

## Sample-informed starting point

The six supplied PDFs have been reviewed locally; see [sample assessment](../SAMPLE-ASSESSMENT.md). Use them as template definitions and negative activation examples, with zero active consent expected. Add form-aware field extraction, cross-page clause grouping, party/representative modeling, separate form/notice versions and policy-controlled withdrawal eligibility to the pilot scope. Existing selected controls are not attributable customer decisions.

The next discovery step is a clause-to-purpose workshop plus authorized completed examples, rather than treating these blank templates as historical grants. Compare completed records from the same template to test false duplicate matches. Accuracy targets remain unevaluated; launch stays TBD.

## Work packages and completion gates

| Phase | Deliverables | Gate before next phase |
|---|---|---|
| 0. Review | This PRD, architecture and approach; confirmed scope and owners | User reviews the plan before implementation |
| 1. Discovery | Source schema and inventory, authorized representative sample, identity mapping, purpose/notice catalog, jurisdictions, downstream map | Agreed formats/languages, activation policy, target load, retention, budget and baseline dataset |
| 2. Extraction pilot | Safe import/conversion, evidence anchors, structured candidates, adjudicated benchmark and review UI design | Targets assessed per format/language; no critical false grants; review staffing and cost acceptable |
| 3. Registry and resolution | Schema, stable IDs, deduplication, identity linking, reviewer workflow, transactional publication and event model | Replays and simultaneous imports create no duplicate records; conflicts cannot silently activate |
| 4. PMP and withdrawal | Authenticated APIs, verified account mapping, purpose-level UI, receipts, outbox and real enforcement adapter(s) | Cross-account access denied; withdrawn status survives concurrency, re-import and delivery outages |
| 5. Production readiness | Load/security/accessibility checks, restore drill, runbooks, alerts and source/consumer reconciliation | Operational owners accept targets and recovery procedure; staged rollout approved |
| 6. Controlled backfill | Small reconciled batches, quality sampling and incremental import | Every source item accounted for; stop if false grants, identity leakage or lost withdrawals occur |

Schema/API drafting and extraction evaluation can proceed alongside each other after scope approval. Publication depends on approved identity and policy rules. Portal launch depends on working downstream enforcement, not only the display page.

## Verification plan

- **Extraction:** template detection, canonical/widget/rendered-value reconciliation, saved defaults and clause classification; native PDFs, scans, mixed pages, DOC/DOCX with images, multi-frame TIFF, rotated/blurred pages, handwriting, missing dates, conflicting text and blank/crossed-out checkboxes. Confirm each enabled format from real sample evidence.
- **Deduplication:** same source replay; identical bytes from different sources; rescans; same name across different people; shared email/phone; one person with multiple purposes; repeated decisions at different times.
- **Publication:** rejected/ambiguous candidates cannot become active; notice matches retain provenance; repeat approval is idempotent; one document can back several scoped decisions.
- **Authorization:** tenants and subjects cannot access each other's records; reviewers have scoped access; evidence views redact other people; extraction text cannot instruct a model to publish data.
- **Withdrawal:** policy eligibility enforcement and rejection/routing of product instructions; verified guardian/representative scopes; repeated requests, withdraw-all, simultaneous publication, old grant re-import, newer verified consent conflict, queue outage, stale event, consumer restart, campaign already queued and database restoration.
- **Operations:** source changes during backfill, worker crash after each stage, partial conversion, poison input, queue replay, dead-letter recovery and manifest reconciliation.

Use synthetic documents for routine tests and explicitly authorized, access-controlled real samples for quality evaluation. Do not expose personal documents to public demo tools.

## Sizing and cost method

Estimate work by pages, not only files: daily documents × average pages × peak factor. Benchmark conversion/OCR seconds per page, extraction API charges, evidence/derivative storage, retries and review minutes. Monthly cost includes initial backfill, incremental OCR, model calls if used, storage, queue/backend infrastructure, monitoring and reviewer labor. Record throughput and accuracy by language/quality to avoid hiding expensive outliers. No numerical budget or vendor decision is justified yet.

## Decisions needed for implementation

| Decision | Why it matters | Proposed owner |
|---|---|---|
| Privacy Management Portal availability and auth integration | Defines where the user views/withdraws and how identity is established | Product / portal owner |
| Source DB/storage and db-consent ownership/schema | Defines connector and migration boundaries | Data / engineering |
| Total documents, pages, languages, handwriting and scan quality | Drives OCR coverage, cost and reviewer staffing | Operations |
| Controller, jurisdiction, historical-form acceptance and retention | Defines activation evidence and storage lifecycle | Privacy / legal owner |
| Purpose/channel and notice-version catalog | Prevents scope guessing and incorrect notice assignment | Privacy / product |
| Identity source and unmatched-person workflow | Prevents wrong-user access and unsafe merges | Identity / portal owner |
| Downstream systems and suppression contract | Makes withdrawal effective in actual processing | Integration owners |
| Cloud, residency, provider data use, budget and launch target | Determines deployable implementation choices | Engineering / sponsor |

## Review checklist

- Confirm that digitizing existing evidence and integrating an existing PMP is the intended scope.
- Review mandatory fields, missing-evidence handling and purpose-level withdrawal behavior in the PRD.
- Confirm the pilot uses human approval and that no fuzzy identity merge occurs automatically.
- Agree which formats/languages and downstream systems the first release must cover.
- Authorize implementation only after these draft decisions are resolved sufficiently to select the stack and delivery scope.
