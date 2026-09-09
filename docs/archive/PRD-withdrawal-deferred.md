> Historical plan: superseded by the current OCR-to-database scope.

# Physical Consent Digitization and Withdrawal — PRD

Status: Draft for review. No application implementation authorized or started.

## 1. Executive Summary

### Problem Statement

Consent already captured on paper is stored as scanned images, PDFs, and Word files. These documents cannot reliably support structured lookup, duplicate detection, or user withdrawal through the PMP portal without extracting and verifying their evidence.

### Proposed Solution

Import existing documents through a read-only connector, extract text and form marks, label consent fields with source evidence, resolve identities and duplicates, and publish approved records into `db-consent`. Expose these records through an authenticated PMP portal where users can withdraw individual purposes and have that decision propagated to dependent systems.

Digitization records historical evidence; it does not collect new consent or prove that every historical form is valid. An unchecked box, missing page, or unreadable signature must never become an inferred grant.

### Working assumptions and decisions to confirm

| Topic | Draft assumption / unresolved decision |
|---|---|
| PMP | Privacy Management Portal (confirmed); whether already implemented, owner, API and login mechanism TBD |
| Source | Database contains document bytes or references to private storage; engine, access method and credentials TBD |
| Destination | `db-consent` is the logical authoritative registry; existing schema and DB engine TBD |
| Scale | Batch backfill followed by incremental imports; total documents, pages/day and peak load TBD |
| Languages | Discover from a representative sample; no unsupported-language auto-approval |
| Governance | Jurisdictions, controller, retention rules, residency and sensitive-data categories TBD |
| Delivery | Launch date: TBD (confirmed by user). Budget, cloud and required stack TBD; no vendor commitment |
| Initial approval | Human approval for every candidate grant in the pilot |

### Success Criteria

These are proposed pilot acceptance targets, not measured results or contractual SLAs.

1. Every published consent has a stable ID, verified subject link, purpose, status, evidence reference and auditable decision; 100% of missing mandatory evidence is held from activation.
2. On at least 500 independently adjudicated consent examples, target ≥98% normalized exact-match precision for populated name/email/phone fields and ≥99% precision for affirmative consent and purpose classification. Report recall and review coverage separately, by format, language and scan quality. If the archive is smaller, label results preliminary.
3. A labeled adversarial suite produces zero false activations, false identity auto-merges, or reactivations from replayed historical documents. Passing a finite suite does not establish zero production risk.
4. Re-importing the same source version or retrying any completed job creates zero additional canonical grants or duplicate lifecycle events.
5. At the agreed pilot load, target p95 ≤2 seconds for portal reads and withdrawal commits; 99% of downstream deliveries acknowledged within 60 seconds. Every failed delivery remains visible and retryable. Capacity and cost/page targets follow the sample benchmark.

### Findings from supplied samples

Six sample PDFs spanning 27 pages have now been inspected; see [sample assessment](../SAMPLE-ASSESSMENT.md) for the page-level field and clause map. They are uncompleted templates with no verified signed customer consent; some interactive controls contain saved selections of unknown provenance. The savings PDF is image-only; corporate and fixed-deposit PDFs have native text and interactive fields. All six are English samples; other formats, languages and completed handwriting remain untested.

The initial pilot must classify template versus completed evidence, distinguish service/product instructions from privacy-consent candidates, and preserve party roles. These exact six samples must yield zero active consent records. Form versions are distinct from privacy-notice versions. Eligibility for a PMP withdrawal action requires an approved clause-to-purpose policy; transaction alerts are candidates for review, not automatically optional privacy consent.

## 2. User Experience & Functionality

### User Personas

- Data operations reviewer: verifies extraction against the original page and resolves exceptions.
- Privacy administrator: manages purposes, notice versions, policy rules and audit exports.
- Data principal: views their consent and withdraws permission through PMP.
- Integration operator: monitors imports, publication, delivery failures and reconciliation.

### User Stories and Acceptance Criteria

**US-01 — Import:** As an integration operator, I want to import existing consent documents so that no source item silently disappears.

- Support scanned and digital PDF, DOCX, legacy DOC, JPEG/JPG, PNG, TIFF/TIF, BMP, WEBP and HEIC/HEIF through a tested converter matrix. Enable a format only after evaluation; route unsupported inputs to an explicit exception.
- Handle multi-page TIFF, PDFs containing both text and scans, embedded images and multiple consent forms in one file. Retain document/page grouping and boundaries.
- Log source system, source record ID, source version, ingestion time, MIME type, checksum and job outcome. Use checkpointed enumeration and a manifest for reconciliation.
- Corrupt, encrypted, oversized, malicious and unsupported files have actionable statuses; no silent skips. Proposed limits: 50 MB and 200 pages/document, configurable after sampling.
- Preserve originals in restricted storage. Importers never update or delete the source archive.

**US-02 — Extract:** As a reviewer, I want labeled fields and highlighted evidence so that I can assess each proposed record.

- Extract the schema below, retaining raw and normalized values, page/region or native-document location, extraction version and per-field confidence.
- Read canonical PDF fields and inherited widget values alongside form-aware rendering; retain appearance/field conflicts for review. Stored or preselected values in an uncompleted template never establish a customer choice.
- Classify clauses as privacy-consent candidates, service preferences, product instructions, declarations, regulatory acknowledgments, receipts or unknown. Account/loan purpose is not automatically a data-processing purpose. “Premature withdrawal” in a fixed-deposit form must never create a privacy-withdrawal event.
- Preserve cross-page clauses and tables. Separate applicant, organization, joint holder, guardian, signatory, claimant, account holder, guarantor, nominee, UBO, witness and bank employee roles. Do not propagate one party’s contacts/signature to another.
- Distinguish granted, declined, unknown and ambiguous evidence; preserve raw checkbox/mark interpretation and the associated statement.
- Missing fields remain null with a reason. Do not invent email, phone, consent date, notice version or purpose. OCR date and import date never substitute for the date of consent.
- Split one form with multiple purposes into independent purpose/channel decisions. Separate multiple people in a document into candidates; uncertain boundaries require review.
- Signature presence can be labeled present/absent/uncertain; signature authentication is outside scope.

**US-03 — Resolve duplicates:** As a reviewer, I want duplicate suggestions without losing legitimate historical decisions.

- Detect duplicate imports by source/version, exact bytes by tenant-scoped SHA-256, and possible rescans by normalized content and page similarity.
- Email/phone/name similarity proposes identity candidates; a name, shared email or phone alone never triggers an automatic merge. Use trusted customer IDs or reviewed identity links.
- A duplicate document can be linked as supporting evidence without creating a new grant. Preserve every source provenance link.
- Same person with a different purpose, controller, notice version, channel or consent event is not discarded as a duplicate. Record conflicts for review.
- Record merge/split decisions and preserve aliases and history; corrections must be reversible and authorization-checked.

**US-04 — Approve:** As a reviewer, I want a side-by-side evidence review so that only justified decisions enter the effective registry.

- Show document, extracted fields, confidence, missing evidence, purpose mapping, identity candidates and duplicate/conflict warnings.
- Require an identified subject, controller, purpose and evidence-backed decision before activation. Required historical date/notice evidence follows an approved policy; unresolved gaps remain held.
- Notice version comes from explicit document evidence or a verified template registry match with provenance. Never substitute the current notice.
- Reviewer can correct, approve, reject or defer with actor/time/reason. Publication is idempotent and transactional.
- Pilot has no automatic grant approval. Later automation requires an evaluated rule set and policy approval.

**US-05 — View:** As a data principal, I want to see my consent so that I understand the permissions recorded for me.

- Authenticate through the agreed identity provider and a verified account-to-subject link. No record discovery by entering another person's email or guessing IDs.
- Show purpose, channel if applicable, status, recorded consent date when known, notice version when known, source summary and withdrawal history.
- Verify delegated/guardian authority independently before any representative accesses or changes another principal’s scopes. A role extracted from a form does not grant portal authority.
- Read current state through the Consent API. Unverified candidates are not displayed as active consent.
- Never expose other people's data from shared pages; redact evidence or show a safe summary. Account recovery or missing identity mapping goes through a defined verification/support flow.

**US-06 — Withdraw:** As a data principal, I want to withdraw one or all available consent scopes so that processing based on those permissions stops.

- Present a clear purpose-level action and optional withdraw-all action, then a durable receipt including timestamp and affected scopes.
- Offer consent withdrawal only for approved eligible scopes. The API must enforce eligibility, not only the UI. Unknown clause policy remains held; product instructions and non-consent records use their designated workflows. Never use this endpoint to withdraw deposit funds, change nomination or close an account. Policy-required service notifications must not be disabled as a side effect.
- Within one transaction, append withdrawal event(s), change current state, establish suppression for those scopes and add outbox events. Return success only after commit.
- A repeat request returns the same outcome without duplicate lifecycle events. Authorization is checked for every affected scope.
- The portal immediately shows withdrawn with downstream delivery tracked separately; failure to synchronize does not restore active status.
- Re-importing old papers cannot reactivate a withdrawn scope. New consent, if introduced later, needs a distinct verified event under an approved re-consent policy.
- Define adapters and owner acknowledgments for every downstream purpose. Withdrawal is not a blanket request to delete all evidence.

**US-07 — Operate and audit:** As an administrator, I want traceable processing and recovery so that I can explain a record's lifecycle.

- Trace source → evidence → extraction version → review → canonical record → lifecycle events → downstream acknowledgment.
- Dashboard reports source reconciliation, exception queues, review aging, unlinked identities, duplicates, OCR costs and delivery latency.
- Retry transient failures with bounded backoff; route exhausted jobs to a dead-letter queue. Replay preserves idempotency and withdrawal precedence.
- Enforce tenant isolation, least privilege, restricted exports and audited evidence access. Retention/deletion policy covers originals, derived text, records and backups.

### Field requirements

| Field | Representation and rule |
|---|---|
| consent_id | Random UUID per canonical consent record; never derived from personal data |
| subject_id | Separate stable UUID; link to verified PMP/customer identity |
| tenant_id / controller_id | Mandatory ownership and processing boundary |
| name | Raw full name plus normalized display name; missing/uncertain permitted during staging |
| email | Raw and validated normalized value; nullable, no guessed corrections |
| phone | Raw plus normalized international value when country context is known; otherwise hold normalization |
| consent decision | Granted / declined / unknown / ambiguous as extracted evidence |
| effective status | Active / withdrawn / expired / superseded; distinct from review status |
| purpose | Raw wording and reviewed canonical purpose_id; granular choices preserved |
| channel | Email/SMS/phone/etc. when stated; absence never means all channels |
| document use / clause type | Template/completed/incomplete/unknown and per-clause routing classification with evidence |
| party / actor / authority | Person vs organization, role, contact ownership, signer and verified representative authority reference |
| withdrawal eligibility | Pending policy / eligible / not managed as consent; policy version, owner and reason |
| form version | Printed form revision, separate from notice_version_id |
| date role | Application, signature, receipt, account opening, maturity and import dates remain distinct |
| notice version | notice_version_id, text/hash or archived reference, mapping evidence; unknown permitted in staging |
| consented_at | Original date/time plus precision/timezone if known; never fabricated |
| evidence | Document ID, source links, original hash, page/region/text anchors and consent wording |
| proof indicators | Checkbox/mark state, signature presence, method such as signed paper; no authenticity claim |
| review metadata | State, reviewer, decision reason, timestamp, rule/model versions |
| lifecycle metadata | created_at, imported_at, updated_at, withdrawn_at, expiry if policy-supported, revision |

Email and phone are desirable fields, not universal prerequisites: historical forms may omit both. Activation still requires a trustworthy subject mapping; unsupported identity links remain unresolved.

### Non-Goals

New consent collection, signature authentication, handwriting-based identity recognition, legal determination by an AI model, broad customer-data cleanup, destruction of original papers, and building a replacement PMP portal are outside this draft scope. Scanning physical paper is upstream; this project consumes digital files. A minimal integration UI may be needed if PMP does not yet exist, subject to a separate scope decision.

## 3. AI System Requirements

### Tool Requirements

Use native text/form extraction with widget-aware rendering and stored-value reconciliation where reliable, with page-level OCR for scans and embedded images. Add layout and checkbox detection, safe Office conversion, optional handwriting recognition for evaluated languages, schema validation and a configurable purpose/notice registry. A structured language model may assist unfamiliar layouts only if benchmark results justify it; provider, residency, retention and cost remain TBD.

All document content is untrusted data. Embedded instructions must not change extraction rules or trigger tools. Extractors get no database write authority, external browsing, secrets or operational tools. Structured outputs must be schema-validated and evidence-linked before review.

### Evaluation Strategy

Build an access-controlled, adjudicated benchmark with format/language/quality/template strata, including blank boxes, crossed-out choices, negations, shared contacts, multiple people, conflicting dates, missing pages and repeat scans. Separate template families across tuning and held-out evaluation where practical. Use two reviewers for disputed labels.

Measure field precision and recall, evidence-location correctness, consent/purpose confusion matrices, duplicate precision/recall, identity false merges, abstention rate, reviewer correction rate, time/page and total cost per accepted record. Report sample counts and uncertainty; measure the untouched extractor separately from the human-approved end result.

Calibrate confidence using labeled examples. Confidence alone cannot approve consent. Low confidence, unsupported layouts, conflicting evidence or missing mandatory fields route to review. Re-run the locked benchmark before any model, prompt, conversion, template or rule change; require no new critical regression.

## 4. Technical Specifications

### Architecture Overview

See [architecture](ARCHITECTURE-withdrawal-deferred.md) and [diagram source](../../diagrams/consent-architecture.mmd).

Read-only connectors enqueue source references. Sandboxed workers validate files, retain evidence, extract native text/OCR and produce candidates. Review and resolution operate in staging. The Consent API publishes approved records to the authoritative registry and serves PMP. A transactional outbox delivers state changes to downstream systems with retries and acknowledgment tracking.

Proposed initial deployment: one modular backend, separate asynchronous document workers, a durable queue, relational `db-consent`, private object storage and an admin review interface. Avoid selecting a cloud or splitting into many services until integration and volume discovery are complete.

### Integration Points

- Source adapters: DB blob, document URI or authorized storage connector; backfill manifest plus change cursor where supported.
- PMP: authenticated API calls plus verified identity mapping; portal cannot write registry tables directly.
- Consent API draft: `GET /v1/me/consents`, `POST /v1/me/withdrawals`, restricted review endpoints and restricted evidence retrieval. Withdrawal body identifies scope IDs and carries an idempotency key; identity comes from the authenticated session.
- Downstream: versioned events with event_id, subject_id, scope, status, revision, effective_at and correlation_id. Minimize personal data in payloads. Consumers deduplicate and reject stale revisions.
- Identity provider: existing OIDC/OAuth mechanism or equivalent, exact integration TBD. Staff access requires role separation and MFA.

### Security & Privacy

Encrypt network traffic and stored data, separate worker/service identities, restrict OCR provider data handling, mask logs, audit original-document access and apply tenant authorization to all queries. Use malware checks, content-type/signature validation, resource limits and isolated conversion with macros disabled and external fetching blocked. This approach follows the [OWASP File Upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

Retention is configurable per approved policy, including temporary images/text, originals, events, suppression records and backups. Restrict immutable history against ordinary edits while providing a governed deletion mechanism when policy requires it. Record keeping and effective withdrawal are informed by [ICO consent-management guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/consent/how-should-we-obtain-record-and-manage-consent/); applicable law and historical-form policy need jurisdiction-specific confirmation. This draft does not certify compliance.

## 5. Risks & Roadmap

### Phased Rollout

1. **Discovery and evidence study:** confirm systems, identity linkage, languages, policy and downstream owners; profile representative forms; establish labeled baseline and capacity/cost envelope.
2. **MVP pilot:** one source connector, tested formats, evidence storage, review queue, duplicate handling, registry and PMP read/withdraw integration. Human approval for all grants. Demonstrate real downstream suppression before production use.
3. **v1.1 controlled rollout:** production backfill in reconciled batches, incremental sync, operational dashboards, restore drills, broader format/language coverage and downstream adapters.
4. **v2.0 evaluated automation:** selected template-based auto-approval only after measured quality and policy acceptance; additional connectors and optional separate re-consent project.

No calendar or budget commitment until discovery is complete. See [implementation approach](APPROACH-withdrawal-deferred.md) for gates and dependencies.

### Technical Risks

| Risk | Mitigation / release gate |
|---|---|
| OCR mistakes turn refusal into permission | Preserve marks and surrounding text; mandatory pilot review; critical-case evaluation |
| Wrong user sees another person's document | Verified identity links, tenant/object authorization and redacted shared evidence |
| Historical notice or consent date missing | Null with reason, template provenance, hold activation pending policy review |
| Fuzzy dedup erases a valid decision | Candidate suggestions only; preserve history and reversible linkage |
| Imported grant overwrites withdrawal | Scope suppression, serialized updates and revision checks; replay/concurrency tests |
| Downstream continues using withdrawn consent | Defined enforcement adapters, acknowledgment/reconciliation and failure runbook |
| Poor scans or handwriting increase cost | Stratified sample, abstention, review capacity measurement, cost/page budget |
| File parser compromise or resource exhaustion | Sandboxed conversion, allowlists and decompression/page/time limits |
| Unknown legacy schema or portal dependency | Agree versioned contracts before implementation; no unsupported stack assumption |
