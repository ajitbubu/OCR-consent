# Data Safeguard

A local React and Python MVP that reads PDF, image and DOCX documents, extracts native PDF fields and OCR text, labels consent-related fields, removes exact duplicate files and stores the result in `db-consent`.

The simple web page shows the source page beside these labeled fields:

- name;
- email;
- phone;
- consent text and observed choice;
- purpose;
- signature presence evidence;
- privacy notice version;
- form version.

Missing or conflicting values remain explicit. Under the configured business rule, detected signature presence sets the consent choice to `yes`. Signature detection does not authenticate the signer or establish signer identity.

## Run locally

Requirements: Python 3.12+, Node.js, npm and either Google Cloud Vision credentials or Tesseract 5.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
cd frontend && npm install && cd ..
```

For Google Cloud Vision, enable the Vision API and provide Application Default Credentials. Then start the API with Google document OCR and the English handwriting hint:

```bash
OCR_PROVIDER=google-vision \
OCR_LANGUAGE_HINTS=en-t-i0-handwrit \
.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8001
```

Set `GOOGLE_CLOUD_VISION_ENDPOINT=us-vision.googleapis.com` or `eu-vision.googleapis.com` when regional processing is required. Set `OCR_PROVIDER=tesseract` for fully local OCR. Google failures stop the processing run unless `OCR_GOOGLE_FALLBACK=true` is explicitly configured.

Start the React page in a second terminal:

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Upload one to five files, or enter a backend-accessible folder containing up to 20 documents and select **Scan folder**. Files already stored in `data/originals` are registered in place, so a folder scan does not create a second copy.

Select a processed record to compare its source page with labeled field details. Choose **JSON Output** to inspect the stable JSON record, **Copy JSON** to copy it, or **Download JSON** to save it. The same output is available from `GET /api/documents/{document_id}/export`; add `?download=true` for an attachment response. The export includes field evidence and OCR provenance but excludes local filesystem paths.

The API can also import document BLOBs from a read-only SQLite source. Supply the database path, table, record-ID column, filename column and BLOB column to `POST /api/import-sqlite`. Other enterprise database engines can use the same staging contract once their connection and schema are known.

The local database and evidence files are created under `data/`:

```text
data/
├── db-consent.sqlite3
├── originals/
└── processed/<document-id>/
```

Set `OCR_DATA_DIR` to put this data elsewhere. Set `VITE_API_URL` when the API is not at `http://localhost:8001`.

## Verify

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
cd frontend && npm run build
```

## OCR providers

The active pilot uses Google Cloud Vision `DOCUMENT_TEXT_DETECTION` with the `en-t-i0-handwrit` hint, supplemented by native PDF extraction, positioned layout recovery and form-aware rendering. Every page stores the provider name and word-confidence average. Tesseract remains available as a configurable local provider or explicit fallback. Categorization is provider-independent and every result remains `needs_review`.

Google setup references: [handwriting OCR](https://docs.cloud.google.com/vision/docs/handwriting) and [Application Default Credentials](https://docs.cloud.google.com/docs/authentication/provide-credentials-adc).

Planning documents:

- [PRD](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Phase plan](docs/APPROACH.md)
- [Technical strategy](docs/TECHNICAL-STRATEGY.md)
- [Sample assessment](docs/SAMPLE-ASSESSMENT.md)
