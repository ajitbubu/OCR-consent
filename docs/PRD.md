# OCR Consent Repository — Product Requirements Document

Status: Proposed MVP plan for approval  
Target launch: TBD  
Pilot size: Six completed sample documents; folder batches support up to 20 documents  
Sample library: Six supplied blank banking form templates, used as layout references and negative examples

## 1. Product goal

Convert existing paper or electronic forms into traceable consent records. The MVP extracts name, email, phone number, signature presence evidence, consent wording and observed choice, purpose and notice/form version, stores candidates in `db-consent`, and displays them on a simple read-only page that can later be incorporated into PMP.

Withdrawal processing, signature authentication, legal consent-validity decisions and downstream enforcement are outside this MVP.

## 2. Why this product is needed

Consent evidence currently exists in PDFs, scans, images and office documents. It cannot be searched reliably and may include handwriting, checkboxes, multiple people, interactive PDF fields and repeated copies. A plain OCR text dump is insufficient because every saved value must retain its person, role, page, location and extraction method.

The six inspected samples total 27 pages. One is image-only, two include interactive form controls and the rest contain native PDF text. The samples are blank or incomplete templates, so they cannot prove extraction accuracy for customer data. Completed or intentionally populated pilot copies are required.

## 3. Users

- **Operator:** uploads documents and resolves processing failures.
- **Reviewer:** compares extracted values with document evidence and corrects them.
- **Data consumer:** views the stored labeled fields on the simple consent page.
- **Administrator/auditor:** manages access and reviews provenance and changes.

## 4. MVP workflow

1. An operator uploads up to five documents or scans up to 20 supported files from a backend-accessible folder.
2. The system validates the files, stores the originals privately and calculates a SHA-256 hash.
3. The extractor reads native PDF text and interactive field/widget values before OCR.
4. Scanned pages are processed with Google Cloud Vision `DOCUMENT_TEXT_DETECTION`; Tesseract remains available for offline use or an explicitly enabled fallback.
5. Required fields are mapped into a fixed schema and validated.
6. Exact duplicate documents are suppressed; possible duplicate people or records are suggested for review and never auto-merged.
7. A reviewer accepts, corrects or rejects each candidate.
8. Stored candidates and their page evidence appear on a simple React page.

## 5. Required capabilities

### 5.1 Ingestion

- Accept PDF, JPEG, PNG, TIFF, WebP and DOCX in the local pilot.
- Import through browser upload, a backend-accessible folder or a read-only SQLite table containing filename and document BLOB columns.
- Preserve source system, source record, source version, MIME type, hash, page count and import time.
- Reject or quarantine corrupt, encrypted, malicious, unsupported or oversized files with a clear outcome.
- Make retries idempotent by source/version and file hash.

### 5.2 Extraction

- Extract native PDF text and canonical/inherited form values.
- Render PDF widgets correctly so checked controls do not disappear.
- OCR printed text locally and preserve PDF selection/widget states. Handwriting and image-based selection-mark quality require managed-provider evaluation.
- Detect signature presence and retain its page evidence. When signature presence is detected, set the observed consent choice to `yes` under the configured business rule. Flag a visible signature area without reliable presence evidence as ambiguous. Do not claim who signed or whether the signature is authentic.
- Retain page number, bounding region or field anchor, raw value, method, processor/model version and confidence for every extracted value.
- Treat document content as untrusted input. It cannot change prompts, execute code or create database queries.

### 5.3 Categorization

The MVP extracts only:

| Field | Required behavior |
|---|---|
| Name | Preserve raw spelling and normalized search value; bind it to a party/role |
| Email | Preserve raw and normalized values; validate format |
| Phone | Preserve raw value; normalize only when country context is known |
| Signature | `present`, `absent`, `unknown` or `ambiguous`; store page evidence, not biometric authentication |
| Consent text | Preserve the exact relevant clause as source evidence |
| Observed choice | `yes` when signature presence is detected; otherwise preserve an explicit `yes` or `no`, or use `unknown`, `ambiguous` or `not_applicable` |
| Purpose | Preserve source wording and map to a controlled category when possible |
| Version/date | Keep form version and privacy notice version separate; nullable when absent |

The system must distinguish privacy consent from declarations, product instructions, service preferences and regulatory acknowledgements. For example, a premature-withdrawal choice is a financial instruction and must not become a privacy consent record.

### 5.4 Review and data quality

- Automatically save candidates as `unreviewed`, `needs_review` or `template_only`.
- Keep every local extraction as `needs_review`; later PMP use must select only appropriately reviewed data.
- Keep corrections, reviewer, time, reason and prior revisions.
- Missing data stays null with a reason: `not_present`, `unreadable`, `ambiguous` or `not_applicable`.
- Blank templates must not create customer identities or affirmative consent.

### 5.5 Consent database

- Use SQLite for the runnable local `db-consent` MVP; retain stable IDs and a schema that can be migrated to PostgreSQL later.
- Use random UUIDs for documents, extraction runs, parties and consent observations.
- Store originals and rendered page evidence under the private local data directory; keep protected references and hashes in `db-consent`.
- Separate raw extraction, normalized candidates and reviewed records.
- Never overwrite a reviewed result when a document is reprocessed.

### 5.6 Simple consent page

- Show the imported document list, processing state and unique document ID.
- Show the rendered source page beside name, email, phone, consent, consent choice, purpose, signature, notice version and form version.
- Show page number, evidence, extraction method, confidence and missing reason.
- Keep this page read-only. Authentication, IDP linkage and withdrawal are future work.

## 6. Success and acceptance criteria

The filled-document pilot passes when:

1. Every input has one explicit result: processed, duplicate, failed, quarantined or unsupported.
2. Every populated field links to a page/region or PDF field and extraction run.
3. Re-uploading the same source/version creates no second logical document or consent observation.
4. Blank fields remain null and blank templates cannot become verified customer records.
5. A reviewer can compare source evidence, correct the candidate and verify it with an audit entry.
6. All stored candidates appear on the local React page with their source page preview.
7. Detected signature presence produces consent choice `yes` with `signature_consent_rule` provenance; signature output does not claim signer identity or authenticity.
8. Provider failures are retryable and never leave a partial record marked verified.

For field quality, the pilot reports exact match/precision/recall per field, consent-choice confusion, evidence-location accuracy, review rate, processing time and provider cost. Five documents demonstrate the workflow, not statistical production accuracy. A production decision requires a larger labeled set, recommended at 20–30 completed examples across layouts and scan qualities.

## 7. Non-functional requirements

- Encryption in transit and at rest, least-privilege service accounts and tenant/ownership isolation.
- Audit logs without raw personal data.
- Configured retention for originals, OCR output, structured data, reviews and backups.
- Provider region and data-handling approval before real customer documents are uploaded.
- Bounded retries, file/resource limits, health checks and observable job states.
- Accessibility target: WCAG 2.1 AA for the reviewer interface.

## 8. Non-goals

- Withdrawal workflow or consent-state enforcement.
- Signature identity/authenticity verification.
- Automatic legal determination that a consent is valid or current.
- Automatic person matching from name/email/phone alone.
- Processing the banking application itself.
- Production PMP integration, IDP authentication or subject matching.
- Multi-cloud OCR, microservices, event streaming or a general customer-master system.

## 9. Delivery

The approved stack and provider strategy are in [TECHNICAL-STRATEGY.md](TECHNICAL-STRATEGY.md). The system design is in [ARCHITECTURE.md](ARCHITECTURE.md), and the phase gates are in [APPROACH.md](APPROACH.md).
