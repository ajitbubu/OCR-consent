# OCR Consent Repository — Technical Strategy

Status: Google Cloud Vision OCR integrated and used on the filled pilot forms

## Current strategy

Use a provider-independent pipeline: native PDF extraction, positioned layout recovery, form-aware rendering, Google Cloud Vision document OCR, conservative labeling, duplicate protection, SQLite storage and a simple React evidence page. Tesseract remains available for local processing and controlled fallback.

The extraction boundary remains replaceable. Google Document AI can be evaluated later on completed handwritten documents while preserving the same database fields and UI.

## Implemented stack

| Layer | Technology | Purpose |
|---|---|---|
| Page | React 19, TypeScript, Vite | Upload/folder intake and simple stored-data display |
| API | Python 3.12+, FastAPI | Ingestion, orchestration and result APIs |
| Database | SQLite `db-consent` | Local pilot records, hashes, fields and evidence metadata |
| PDF processing | pypdf, pypdfium2 | Embedded text, interactive widgets and page rendering |
| Primary OCR | Google Cloud Vision `DOCUMENT_TEXT_DETECTION` | Printed and handwritten document extraction |
| Local OCR | Tesseract 5 through pytesseract | Offline processing and explicit fallback |
| Images and DOCX | Pillow, python-docx | Image normalization, previews and document text/images |
| Tests | pytest and TypeScript/Vite build | Field rules, blank values, signature semantics, duplicate safety and UI compilation |

## Extraction sequence

1. Validate and hash the source file.
2. Preserve the original using a generated UUID.
3. For PDFs, extract native text and widget values before rendering.
4. Render every page with PDF form appearances enabled.
5. OCR the page image with the configured provider and keep page-level confidence and provider provenance.
6. Label explicit name, email, phone, consent, purpose, signature, notice-version and form-version evidence.
7. Keep missing and conflicting values explicit.
8. Persist pages, fields, clauses and processor provenance.
9. Show the result and page image on the React page.

## Signature strategy

The signature field records presence evidence. A non-empty PDF signature widget or OCR signature-presence rule can produce `present`. The configured business rule then sets `consent_choice` to `yes`, carries over the signature page and confidence, and records `signature_consent_rule` provenance. A visible signature label without reliable presence evidence produces `ambiguous` and must be reviewed. The MVP never authenticates a signer or establishes signer identity.

Reliable handwritten signature-region detection should be evaluated with a managed document model or a labeled computer-vision detector. It must retain a bounding region and reviewer confirmation.

## Managed OCR evaluation

Google Cloud Vision is now the primary pilot OCR provider. The next decision is based on a verified answer sheet: compare Google Vision with Tesseract by field exact match, consent evidence accuracy, signature-presence accuracy, review rate, latency and cost. Google Document AI remains a later candidate if form-specific extraction or stronger layout structure is required.

Based on Google's published list pricing, the first 1,000 Enterprise OCR pages are free and Custom Extractor processing is $30 per 1,000 pages. A custom processor can also incur an hourly hosting charge. These prices must be rechecked in the selected project.

References:

- [Enterprise Document OCR](https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr)
- [Custom Extractor with generative AI](https://docs.cloud.google.com/document-ai/docs/ce-with-genai)
- [Document AI pricing](https://cloud.google.com/products/document-ai/pricing)

## Deferred items

- Production PMP integration and IDP authentication.
- Withdrawal and downstream actions.
- Automatic identity matching.
- PostgreSQL/object storage migration.
- Distributed queues and multiple workers.
- General-purpose LLM categorization.

The current React page is sufficient to inspect what a future PMP could consume.
