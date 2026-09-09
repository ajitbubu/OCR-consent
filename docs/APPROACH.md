# OCR Consent Repository — Phase Plan

Status: Local MVP phases 1–7 implemented

## Phase 1 — Foundation — Complete

- React 19 + TypeScript + Vite page.
- Python 3.12 + FastAPI service.
- Local SQLite `db-consent` and private `data/` directory.
- Health, list and detail APIs.

Completion evidence: backend compiles and the frontend production build succeeds.

## Phase 2 — File and folder ingestion — Complete

- Upload one to five PDF, image or DOCX files.
- Read up to 20 supported files from a backend-accessible folder without duplicating files that are already in `data/originals`.
- Read up to five document BLOBs from a configured SQLite table in read-only mode.
- Validate extension, empty files and 50 MB limit.
- Generate document UUID, store the original and calculate SHA-256.
- Return the existing document for an exact duplicate.

Completion evidence: duplicate, folder-adoption and read-only SQLite BLOB import tests pass. The six filled forms have unique stored document records.

## Phase 3 — Native extraction and OCR — Complete

- Read native PDF text, positioned layout text and interactive widget states.
- Open AES PDFs that permit an empty password.
- Render pages with form appearances enabled.
- OCR rendered pages with Google Cloud Vision `DOCUMENT_TEXT_DETECTION` and retain Tesseract as a configurable local provider.
- Read DOCX text/tables and OCR embedded images.
- Save page previews and page-level confidence.

Completion evidence: the image-only savings form and the four native-text forms all reach `completed`.

## Phase 4 — Required-field labeling — Complete for baseline

- Label name, email, phone, consent text, observed consent choice, purpose, signature presence evidence, notice version and form version.
- Categorize consent candidates, service preferences, declarations, product instructions and purpose context.
- Preserve raw value, source page, evidence, confidence, missing reason and extraction method.
- Leave blank or conflicting values null.

Completion evidence: tests cover explicit fields, blank forms and signature-widget semantics. The supplied blank templates create no invented customer names, emails, phones or choices.

## Phase 5 — Database persistence and duplicate safety — Complete

- Store documents, sources, extraction runs, pages, fields and clauses.
- Write extraction results transactionally.
- Keep job and review states separate.
- Prevent duplicate files by SHA-256.

Completion evidence: the local database contains six completed filled-form records and their 27 rendered pages, in addition to the earlier blank-template records.

## Phase 6 — Simple consent page — Complete

- Show upload and folder controls.
- Show all database documents and processing status.
- Show a rendered page next to the labeled fields.
- Show detected clauses and processing notes.
- Poll while OCR is running.
- Provide responsive mobile and desktop layouts.

Completion evidence: the API and web page expose the completed documents, source-page rendering and the required-field cards.

## Phase 7 — Local pilot — Complete for supplied templates and filled forms

Processed:

1. Account opening — savings.
2. Account opening — corporate.
3. Fixed deposit application.
4. Unclaimed deposit application.
5. Loan application.

The first supplied files were blank templates. Six filled forms have now also been processed: the five form types above plus the MSME loan application. They exercise positioned PDF values, handwriting OCR, consent/declaration evidence and signature-presence rules. Missing fields and conflicts remain explicitly marked for review.

## Phase 8 — Google Cloud Vision integration — Complete; benchmark next

- Select Google Cloud Vision or Tesseract through `OCR_PROVIDER`.
- Use `DOCUMENT_TEXT_DETECTION` with configurable language hints and regional endpoint.
- Record the provider on each processing run and page-level word confidence.
- Stop on Google errors by default; permit local fallback only through explicit configuration.
- Compare Tesseract and Google against a verified answer sheet for field accuracy, evidence location, review rate, time and cost.
- Keep managed output in `needs_review`.

Current evidence: six filled forms and 27 pages completed with Google Vision. Exit gate: provider quality selected from measured field-level results, with the production endpoint and data handling approved.

## Phase 9 — Review editing — Later

- Allow staff to correct extracted values.
- Add accept/reject/verify actions and immutable history.
- Add near-duplicate suggestions without automatic person merges.

Exit gate: every correction has actor, time, reason and prior value.

## Phase 10 — Production integration — Later

- Move SQLite to PostgreSQL when concurrency requires it.
- Add durable workers, object storage, monitoring, backup/restore and retention.
- Connect the real source database through a read-only adapter.
- Provide a stable API for PMP after its identity and authorization contract is defined.

Withdrawal, IDP integration and downstream consent actions remain outside the OCR MVP.

## Verification commands

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
cd frontend && npm run build
```
