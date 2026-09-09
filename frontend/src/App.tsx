import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

type DocumentSummary = {
  id: string;
  filename: string;
  extension: string;
  status: "queued" | "processing" | "completed" | "failed";
  review_status: string;
  document_type: string;
  page_count: number;
  field_count: number;
  error?: string | null;
  updated_at: string;
};

type Field = {
  id: string;
  name: string;
  category: string;
  value: string | null;
  raw_value: string | null;
  page: number | null;
  evidence: string;
  confidence: number | null;
  missing_reason: string | null;
  provenance: string;
};

type Clause = {
  id: string;
  category: string;
  text: string;
  page: number;
};

type Page = {
  id: string;
  number: number;
  method: string;
  confidence: number | null;
  widgets: Array<{ name: string; value: string }>;
};

type DocumentDetail = DocumentSummary & {
  warnings: string[];
  fields: Field[];
  clauses: Clause[];
  pages: Page[];
};

type DocumentExport = {
  schema_version: string;
  record_id: string;
  source: Record<string, unknown>;
  processing: Record<string, unknown>;
  fields: Record<string, Record<string, unknown>>;
  clauses: Array<Record<string, unknown>>;
  pages: Array<Record<string, unknown>>;
  warnings: string[];
};

const fieldLabels: Record<string, string> = {
  name: "Name",
  email: "Email",
  phone: "Phone",
  consent: "Consent text",
  consent_choice: "Consent choice",
  purpose: "Purpose",
  signature: "Signature",
  notice_version: "Notice version",
  form_version: "Form version",
};

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function StatusPill({ status }: { status: string }) {
  return <span className={`status status--${status}`}>{status.replaceAll("_", " ")}</span>;
}

function FieldCard({ field }: { field: Field }) {
  const value = field.value || "Not found";
  return (
    <article className={`field-card ${field.value ? "" : "field-card--missing"}`}>
      <div className="field-card__heading">
        <span>{fieldLabels[field.name] ?? field.name}</span>
        {field.page && <span className="page-chip">Page {field.page}</span>}
      </div>
      <p className="field-card__value">{value}</p>
      {!field.value && (
        <p className="field-card__reason">
          {field.missing_reason?.replaceAll("_", " ") ?? "Not available"}
        </p>
      )}
      {field.evidence && <p className="field-card__evidence">{field.evidence}</p>}
      <div className="field-card__meta">
        <span>{field.provenance.replaceAll("_", " ")}</span>
        {field.confidence !== null && <span>{Math.round(field.confidence)}% OCR confidence</span>}
      </div>
    </article>
  );
}

function DetailPanel({ detail }: { detail: DocumentDetail }) {
  const [page, setPage] = useState(1);
  const [view, setView] = useState<"fields" | "json">("fields");
  const [exportData, setExportData] = useState<DocumentExport | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [copyMessage, setCopyMessage] = useState("");

  useEffect(() => {
    setPage(detail.pages[0]?.number ?? 1);
    setView("fields");
    setExportData(null);
    setExportError(null);
    setCopyMessage("");
    const controller = new AbortController();
    api<DocumentExport>(`/api/documents/${detail.id}/export`, { signal: controller.signal })
      .then(setExportData)
      .catch((error) => {
        if (error.name !== "AbortError") setExportError(error.message);
      });
    return () => controller.abort();
  }, [detail.id, detail.pages]);

  const jsonText = exportData ? JSON.stringify(exportData, null, 2) : "";

  async function copyJson() {
    if (!jsonText) return;
    try {
      await navigator.clipboard.writeText(jsonText);
      setCopyMessage("JSON copied");
    } catch {
      setCopyMessage("Copy failed. Use Download JSON instead.");
    }
  }

  return (
    <section className="detail" aria-labelledby="detail-title">
      <header className="detail__header">
        <div>
          <p className="eyebrow">Simple PMP data view</p>
          <h2 id="detail-title">{detail.filename}</h2>
          <p className="detail__meta">
            {detail.document_type} · {detail.page_count} pages · Updated {formatDate(detail.updated_at)}
          </p>
        </div>
        <div className="detail__actions">
          <div className="status-stack">
            <StatusPill status={detail.status} />
            <StatusPill status={detail.review_status} />
          </div>
          <a
            className="button-link"
            href={`${API_URL}/api/documents/${detail.id}/export?download=true`}
          >
            Download JSON
          </a>
        </div>
      </header>

      {detail.error && <div className="alert alert--error">{detail.error}</div>}

      <div className="workspace">
        <div className="evidence-panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">Source evidence</p>
              <h3>Document page</h3>
            </div>
            {detail.pages.length > 1 && (
              <label className="page-select">
                <span>Page</span>
                <select value={page} onChange={(event) => setPage(Number(event.target.value))}>
                  {detail.pages.map((item) => (
                    <option key={item.id} value={item.number}>
                      {item.number}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {detail.pages.length ? (
            <img
              className="page-image"
              src={`${API_URL}/api/documents/${detail.id}/pages/${page}/image`}
              alt={`Rendered page ${page} of ${detail.filename}`}
              width="1300"
              height="1800"
              loading="lazy"
            />
          ) : (
            <div className="page-placeholder">The preview will appear when OCR completes.</div>
          )}
        </div>

        <div className="result-panel">
          <div className="section-title">
            <div>
              <p className="eyebrow">Extraction output</p>
              <h3>{view === "fields" ? "Labeled Fields" : "JSON Record"}</h3>
            </div>
            <span className="record-id" title={detail.id}>
              ID {detail.id.slice(0, 8)}
            </span>
          </div>

          <div className="view-tabs" role="tablist" aria-label="Output format">
            <button
              type="button"
              role="tab"
              aria-selected={view === "fields"}
              className={view === "fields" ? "view-tab view-tab--active" : "view-tab"}
              onClick={() => setView("fields")}
            >
              Field Details
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={view === "json"}
              className={view === "json" ? "view-tab view-tab--active" : "view-tab"}
              onClick={() => setView("json")}
            >
              JSON Output
            </button>
          </div>

          {view === "fields" ? (
            <div className="field-grid" role="tabpanel">
              {detail.fields.map((field) => (
                <FieldCard field={field} key={field.id} />
              ))}
            </div>
          ) : (
            <div className="json-panel" role="tabpanel">
              <div className="json-panel__toolbar">
                <span>Schema {exportData?.schema_version ?? "1.0"}</span>
                <button type="button" onClick={copyJson} disabled={!exportData}>
                  Copy JSON
                </button>
              </div>
              <div className="sr-status" aria-live="polite">{copyMessage}</div>
              {exportError ? (
                <div className="alert alert--error">{exportError} Refresh the page and try again.</div>
              ) : exportData ? (
                <pre className="json-output"><code>{jsonText}</code></pre>
              ) : (
                <div className="json-loading">Preparing JSON…</div>
              )}
            </div>
          )}
        </div>
      </div>

      {view === "fields" && !!detail.clauses.length && (
        <section className="clauses">
          <div className="section-title">
            <div>
              <p className="eyebrow">Context retained for review</p>
              <h3>Detected clauses</h3>
            </div>
          </div>
          <div className="clause-list">
            {detail.clauses.slice(0, 12).map((clause) => (
              <article className="clause" key={clause.id}>
                <div>
                  <span className="clause__category">{clause.category}</span>
                  <span className="page-chip">Page {clause.page}</span>
                </div>
                <p>{clause.text}</p>
              </article>
            ))}
          </div>
        </section>
      )}

      {view === "fields" && !!detail.warnings.length && (
        <details className="warnings">
          <summary>Processing notes ({detail.warnings.length})</summary>
          <ul>
            {detail.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [folder, setFolder] = useState("");
  const [search, setSearch] = useState("");
  const [ocrProvider, setOcrProvider] = useState("OCR service");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadDocuments = useCallback(async (signal?: AbortSignal) => {
    const response = await fetch(`${API_URL}/api/documents`, { signal });
    if (!response.ok) throw new Error("Could not load documents.");
    const items = (await response.json()) as DocumentSummary[];
    setDocuments(items);
    setSelectedId((current) => current ?? items[0]?.id ?? null);
    return items;
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadDocuments(controller.signal).catch((error) => {
      if (error.name !== "AbortError") setMessage(error.message);
    });
    return () => controller.abort();
  }, [loadDocuments]);

  useEffect(() => {
    api<{ ocr_provider: string }>("/api/health")
      .then((health) => setOcrProvider(health.ocr_provider.replaceAll("-", " ")))
      .catch(() => undefined);
  }, []);

  const processing = useMemo(
    () => documents.some((item) => item.status === "queued" || item.status === "processing"),
    [documents],
  );

  const visibleDocuments = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return documents;
    return documents.filter(
      (item) =>
        item.filename.toLowerCase().includes(query) ||
        item.document_type.toLowerCase().includes(query),
    );
  }, [documents, search]);

  useEffect(() => {
    if (!processing) return;
    const interval = window.setInterval(() => loadDocuments().catch(() => undefined), 2000);
    return () => window.clearInterval(interval);
  }, [loadDocuments, processing]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    const controller = new AbortController();
    fetch(`${API_URL}/api/documents/${selectedId}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Could not load the selected document.");
        return response.json() as Promise<DocumentDetail>;
      })
      .then(setDetail)
      .catch((error) => {
        if (error.name !== "AbortError") setMessage(error.message);
      });
    return () => controller.abort();
  }, [selectedId, documents]);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("documents") as HTMLInputElement;
    if (!input.files?.length) return;
    setBusy(true);
    setMessage(null);
    const body = new FormData();
    Array.from(input.files)
      .slice(0, 5)
      .forEach((file) => body.append("files", file));
    try {
      const result = await api<{ documents: Array<{ id: string; duplicate: boolean }> }>("/api/documents", {
        method: "POST",
        body,
      });
      setSelectedId(result.documents[0]?.id ?? null);
      setMessage(`${result.documents.length} document(s) accepted for processing.`);
      input.value = "";
      await loadDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function scanFolder() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await api<{ documents: Array<{ id: string }>; folder: string }>("/api/import-folder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: folder, limit: 20 }),
      });
      setSelectedId(result.documents[0]?.id ?? null);
      setMessage(`${result.documents.length} document(s) found in ${result.folder}.`);
      await loadDocuments();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Folder import failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to Main Content</a>
      <header className="topbar">
        <div className="brand">
          <h1><img className="brand-logo" src="/dsg-logo.png" alt="Data Safeguard" width="4000" height="1000" /></h1>
          <p className="eyebrow">Privacy document intelligence</p>
        </div>
        <div className="topbar__summary">
          <span className="provider-chip"><span className="provider-dot" />{ocrProvider}</span>
          <strong>{documents.length}</strong>
          <span>records</span>
        </div>
      </header>

      <main id="main-content">
        <section className="ingest-card" aria-labelledby="ingest-title">
          <div className="ingest-card__intro">
            <p className="eyebrow">Step 1 · Add Source Documents</p>
            <h2 id="ingest-title">Import Consent Records</h2>
            <p>Upload documents or scan a server folder. Google Vision reads each page and the labeled result is saved in db-consent.</p>
          </div>
          <div className="source-options">
            <form className="source-card upload-control" onSubmit={upload}>
              <div className="source-card__heading">
                <span className="source-number">A</span>
                <div>
                  <strong>Upload Files</strong>
                  <span>PDF, images, or Word · up to 5 files</span>
                </div>
              </div>
              <label className="file-picker" htmlFor="documents">Choose Documents</label>
              <input id="documents" name="documents" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp,.docx" />
              <button type="submit" disabled={busy}>{busy ? "Processing…" : "Upload & Extract"}</button>
            </form>
            <div className="source-card folder-control">
              <div className="source-card__heading">
                <span className="source-number">B</span>
                <div>
                  <strong>Connect Folder</strong>
                  <span>Read up to 20 files from the server</span>
                </div>
              </div>
              <label htmlFor="folder">Server folder path</label>
              <div>
                <input
                  id="folder"
                  name="folder"
                  value={folder}
                  placeholder="/path/to/document-folder…"
                  aria-describedby="folder-help"
                  autoComplete="off"
                  spellCheck={false}
                  onChange={(event) => setFolder(event.target.value)}
                />
                <button
                  type="button"
                  className="button--secondary"
                  onClick={scanFolder}
                  disabled={busy || !folder.trim()}
                >
                  {busy ? "Processing…" : "Scan Folder"}
                </button>
              </div>
              <p id="folder-help" className="folder-help">
                Enter the full path to a folder on the computer running this app, then click Scan Folder.
                <br />
                Example on Mac: <code>/Users/yourname/Downloads/ConsentForms</code>
                <br />
                In Finder, select the folder and press Option + Command + C to copy its path.
                If the app runs on a remote server, use Upload Files for documents on your computer.
              </p>
            </div>
          </div>
          {message && <div className="alert" role="status" aria-live="polite">{message}</div>}
        </section>

        <div className="content-grid">
          <aside className="document-list" aria-label="Imported documents">
            <div className="document-list__header">
              <div>
                <p className="eyebrow">db-consent</p>
                <h2>Documents</h2>
              </div>
              {processing && <span className="processing-dot" role="status" aria-label="OCR is running" />}
            </div>
            <div className="document-search">
              <label htmlFor="document-search">Search records</label>
              <input
                id="document-search"
                name="document-search"
                type="search"
                value={search}
                placeholder="Search filename or type…"
                autoComplete="off"
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            {visibleDocuments.length ? (
              <div className="document-list__items">
                {visibleDocuments.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    className={`document-row ${item.id === selectedId ? "document-row--selected" : ""}`}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <span className="document-row__icon">{item.extension?.replace(".", "").toUpperCase() || "DOC"}</span>
                    <span className="document-row__copy">
                      <strong>{item.filename}</strong>
                      <span>{item.document_type}</span>
                    </span>
                    <StatusPill status={item.status} />
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-list">{documents.length ? "No matching records." : "No documents imported yet."}</div>
            )}
          </aside>

          {detail ? (
            <DetailPanel detail={detail} />
          ) : (
            <section className="empty-detail">
              <div className="empty-detail__icon">⌁</div>
              <h2>Select or import a document</h2>
              <p>The extracted fields and page evidence will appear here.</p>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
