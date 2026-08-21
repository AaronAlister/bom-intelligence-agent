import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

import type { WorkspaceView } from "../App";
import type { IngestionResult } from "../types/bom";

type BOMAnalysisProps = {
  onNavigate: (view: WorkspaceView) => void;
  onLogout: () => void;
  onIngested: (result: IngestionResult) => void;
  ingestionResult: IngestionResult | null;
};

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "";

const SUPPORTED_EXTENSIONS = [".csv", ".tsv", ".xlsx", ".xls", ".xml", ".json"];

type ValidationIssue = {
  row_number: number;
  field: string;
  message: string;
  severity: string;
};

type ValidationErrorDetail = {
  message?: unknown;
  invalid_rows?: unknown;
  total_rows?: unknown;
  validation_issues?: unknown;
};

function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf(".");
  if (lastDot === -1) return "";
  return filename.slice(lastDot).toLowerCase();
}

export default function BOMAnalysis({
  onNavigate,
  onLogout,
  onIngested,
  ingestionResult,
}: BOMAnalysisProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<IngestionResult | null>(null);
  const [error, setError] = useState("");
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>(
    [],
  );
  const [isUploading, setIsUploading] = useState(false);

  // Sync with persisted BOM
  useEffect(() => {
    setResult(ingestionResult);
  }, [ingestionResult]);

  const handleFile = (file: File | undefined) => {
    if (!file) return;
    const extension = getFileExtension(file.name);
    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
      setSelectedFile(null);
      setResult(null);
      setError(
        "Unsupported file format. Use CSV, TSV, XLSX, XLS, XML, or JSON.",
      );
      setValidationIssues([]);
      return;
    }
    setSelectedFile(file);
    setResult(null);
    setError("");
    setValidationIssues([]);
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    handleFile(event.target.files?.[0]);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    handleFile(event.dataTransfer.files[0]);
  };

  const handleBrowse = () => {
    fileInputRef.current?.click();
  };

  const handleUpload = async () => {
    if (!selectedFile || isUploading) return;

    setIsUploading(true);
    setError("");
    setResult(null);
    setValidationIssues([]);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${API_BASE_URL}/api/v1/boms/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let message = `Upload failed with status ${response.status}.`;

        try {
          const errorBody: unknown = await response.json();

          if (
            typeof errorBody === "object" &&
            errorBody !== null &&
            "detail" in errorBody
          ) {
            const detail = (errorBody as { detail?: unknown }).detail;

            if (typeof detail === "string") {
              message = detail;
            } else if (typeof detail === "object" && detail !== null) {
              const structuredDetail = detail as ValidationErrorDetail;

              if (typeof structuredDetail.message === "string") {
                message = structuredDetail.message;
              }

              if (Array.isArray(structuredDetail.validation_issues)) {
                const issues = structuredDetail.validation_issues.filter(
                  (issue): issue is ValidationIssue => {
                    if (typeof issue !== "object" || issue === null) {
                      return false;
                    }
                    const candidate = issue as Partial<ValidationIssue>;
                    return (
                      typeof candidate.row_number === "number" &&
                      typeof candidate.field === "string" &&
                      typeof candidate.message === "string" &&
                      typeof candidate.severity === "string"
                    );
                  },
                );
                setValidationIssues(issues);
              }

              if (
                typeof structuredDetail.invalid_rows === "number" &&
                typeof structuredDetail.total_rows === "number"
              ) {
                message += ` ${structuredDetail.invalid_rows} of ${structuredDetail.total_rows} rows are invalid.`;
              }
            }
          }
        } catch {
          // Keep the default HTTP error message.
        }

        throw new Error(message);
      }

      const ingestionResult = (await response.json()) as IngestionResult;
      setResult(ingestionResult);
      onIngested(ingestionResult);
    } catch (uploadError: unknown) {
      if (uploadError instanceof TypeError) {
        setError(
          "Unable to reach the BOM Intelligence backend. Make sure the backend is running.",
        );
      } else if (uploadError instanceof Error) {
        setError(uploadError.message);
      } else {
        setError("BOM upload failed.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setResult(null);
    setError("");
    setValidationIssues([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="bi-dashboard">
      <aside className="bi-sidebar">
        <div className="bi-sidebar-brand">
          <div className="bi-brand-mark" aria-hidden="true">
            <span />
          </div>
          <div>
            <strong>BOM INTELLIGENCE</strong>
            <span>AGENT PLATFORM</span>
          </div>
        </div>

        <div className="bi-nav-section">
          <span className="bi-nav-label">WORKSPACE</span>
          <nav className="bi-nav" aria-label="Workspace navigation">
            {[
              ["Dashboard", "▦", "dashboard"],
              ["BOM Analysis", "▤", "bom-analysis"],
              ["Components", "◈", "components"],
              ["Risk Intelligence", "△", "risk"],
              ["Alternatives", "⇄", "alternatives"],
              ["Lifecycle", "◷", "lifecycle"],
              ["Reports", "▥", "reports"],
            ].map(([label, icon, target]) => (
              <button
                key={label}
                className={`bi-nav-item ${target === "bom-analysis" ? "active" : ""}`}
                type="button"
                onClick={() => onNavigate(target as WorkspaceView)}
              >
                <span className="bi-nav-icon" aria-hidden="true">
                  {icon}
                </span>
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="bi-sidebar-bottom">
          <div className="bi-system-card">
            <div className="bi-system-title">
              <span className="bi-live-dot" />
              <span>All systems operational</span>
            </div>
            <div className="bi-system-services">
              <span>API</span>
              <span>Database</span>
              <span>RAG</span>
              <span>Worker</span>
            </div>
          </div>
          <button className="bi-signout" type="button" onClick={onLogout}>
            <span aria-hidden="true">↪</span>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="bi-main">
        <header className="bi-topbar">
          <div className="bi-breadcrumb">
            <span>Workspace</span>
            <b>/</b>
            <strong>BOM Analysis</strong>
          </div>
          <div className="bi-topbar-actions">
            <div className="bi-live">
              <span className="bi-live-dot" />
              <span>LIVE</span>
            </div>
            <button
              className="bi-notification"
              type="button"
              aria-label="Notifications"
            >
              ♧<span>0</span>
            </button>
            <button className="bi-profile" type="button" aria-label="Account">
              <span>AA</span>
            </button>
          </div>
        </header>

        <div className="bi-content">
          <div className="bi-page-heading">
            <div>
              <span className="bi-eyebrow">ENGINEERING WORKSPACE</span>
              <h1>BOM Analysis</h1>
            </div>
            <p>
              Upload a bill of materials to begin component intelligence,
              procurement risk and lifecycle analysis.
            </p>
          </div>

          <section className="bom-upload-layout">
            <article className="bi-panel bom-upload-panel">
              <div className="bi-panel-header">
                <div>
                  <div className="bi-panel-title">
                    <span aria-hidden="true">▤</span>
                    <span>BOM INGESTION</span>
                  </div>
                  <h2>
                    {result ? "BOM successfully ingested" : "Upload a BOM"}
                  </h2>
                </div>
                <span className="bi-analysis-badge">
                  {isUploading ? "PROCESSING" : result ? "INGESTED" : "READY"}
                </span>
              </div>

              <input
                ref={fileInputRef}
                className="bom-file-input"
                type="file"
                accept={SUPPORTED_EXTENSIONS.join(",")}
                onChange={handleFileChange}
              />

              {!result && (
                <div
                  className={`bom-dropzone ${selectedFile ? "has-file" : ""}`}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={handleDrop}
                >
                  <div className="bom-upload-icon" aria-hidden="true">
                    ↑
                  </div>
                  <h3>
                    {selectedFile
                      ? selectedFile.name
                      : "Drop your BOM file here"}
                  </h3>
                  <p>
                    {selectedFile
                      ? `${(selectedFile.size / 1024).toFixed(1)} KB selected`
                      : "Drag and drop your file here, or browse from your computer."}
                  </p>
                  <button
                    className="bom-browse-button"
                    type="button"
                    onClick={handleBrowse}
                    disabled={isUploading}
                  >
                    {selectedFile ? "CHOOSE DIFFERENT FILE" : "BROWSE FILES"}
                  </button>
                  <span className="bom-file-note">
                    Supported formats: CSV, TSV, XLSX, XLS, XML, JSON
                  </span>
                </div>
              )}

              {isUploading && (
                <div className="bom-processing-state">
                  <div className="bom-processing-indicator" />
                  <strong>Processing {selectedFile?.name}</strong>
                  <span>
                    Validating, normalizing and ingesting BOM components...
                  </span>
                </div>
              )}

              {result && (
                <div className="bom-result-card">
                  <div className="bom-result-header">
                    <div className="bom-result-heading">
                      <span className="bi-eyebrow">INGESTION RESULT</span>
                      <h3 className="bom-result-title">Ingestion complete</h3>
                      <span className="bom-result-file">
                        {result.source_file}
                      </span>
                    </div>
                    <span className="bom-result-status">INGESTED</span>
                  </div>

                  <div className="bom-result-success">
                    <span
                      className="bom-result-success-icon"
                      aria-hidden="true"
                    >
                      ✓
                    </span>
                    <div className="bom-result-success-copy">
                      <strong>BOM successfully processed</strong>
                      <span>
                        The BOM is validated and ready for intelligence
                        analysis.
                      </span>
                    </div>
                  </div>

                  <div className="bom-result-metrics">
                    <div className="bom-result-metric">
                      <span className="bom-result-metric-label">
                        Components
                      </span>
                      <strong className="bom-result-metric-value">
                        {result.components.length}
                      </strong>
                    </div>
                    <div className="bom-result-metric">
                      <span className="bom-result-metric-label">
                        Total Rows
                      </span>
                      <strong className="bom-result-metric-value">
                        {result.total_rows}
                      </strong>
                    </div>
                    <div className="bom-result-metric">
                      <span className="bom-result-metric-label">
                        Valid Rows
                      </span>
                      <strong className="bom-result-metric-value success">
                        {result.valid_rows}
                      </strong>
                    </div>
                    <div className="bom-result-metric">
                      <span className="bom-result-metric-label">
                        Invalid Rows
                      </span>
                      <strong
                        className={`bom-result-metric-value ${
                          result.invalid_rows > 0 ? "warning" : "success"
                        }`}
                      >
                        {result.invalid_rows}
                      </strong>
                    </div>
                  </div>

                  <div className="bom-result-id">
                    <span className="bom-result-id-label">BOM ID</span>
                    <code className="bom-result-id-value">{result.bom_id}</code>
                  </div>

                  <div className="bom-result-actions">
                    <button
                      className="bom-secondary-button"
                      type="button"
                      onClick={resetUpload}
                    >
                      UPLOAD ANOTHER
                    </button>
                    <button
                      className="bi-primary-button"
                      type="button"
                      onClick={() => onNavigate("dashboard")}
                    >
                      <span>VIEW DASHBOARD</span>
                      <span aria-hidden="true">→</span>
                    </button>
                  </div>
                </div>
              )}

              {error && (
                <div
                  className={
                    validationIssues.length > 0
                      ? "bom-validation-error"
                      : "bom-upload-error"
                  }
                  role="alert"
                >
                  <div className="bom-validation-error-header">
                    <div
                      className="bom-validation-error-icon"
                      aria-hidden="true"
                    >
                      !
                    </div>

                    <div>
                      <strong>
                        {validationIssues.length > 0
                          ? "BOM validation failed"
                          : "Upload failed"}
                      </strong>

                      <span>{error}</span>
                    </div>
                  </div>

                  {validationIssues.length > 0 && (
                    <div className="bom-validation-issues">
                      <div className="bom-validation-issues-header">
                        <span>ROW</span>
                        <span>FIELD</span>
                        <span>ISSUE</span>
                        <span>SEVERITY</span>
                      </div>

                      {validationIssues.map((issue, index) => (
                        <div
                          className="bom-validation-issue"
                          key={`${issue.row_number}-${issue.field}-${index}`}
                        >
                          <span className="bom-validation-row">
                            {issue.row_number}
                          </span>

                          <span className="bom-validation-field">
                            {issue.field}
                          </span>

                          <span className="bom-validation-message">
                            {issue.message}
                          </span>

                          <span
                            className={`bom-validation-severity bom-validation-severity--${issue.severity.toLowerCase()}`}
                          >
                            {issue.severity}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {validationIssues.length > 0 && (
                    <p className="bom-validation-help">
                      Fix the highlighted issues in your BOM and upload the file
                      again.
                    </p>
                  )}
                </div>
              )}

              {!result && (
                <div className="bom-upload-actions">
                  <button
                    className="bi-primary-button"
                    type="button"
                    disabled={!selectedFile || isUploading}
                    onClick={handleUpload}
                  >
                    <span>
                      {isUploading ? "ANALYZING BOM..." : "ANALYZE BOM"}
                    </span>
                    <span aria-hidden="true">{isUploading ? "…" : "→"}</span>
                  </button>
                </div>
              )}
            </article>

            <article className="bi-panel bom-info-panel">
              <div className="bi-panel-header">
                <div>
                  <div className="bi-panel-title">
                    <span aria-hidden="true">◇</span>
                    <span>ANALYSIS PIPELINE</span>
                  </div>
                  <h2>What happens next</h2>
                </div>
              </div>
              <div className="bom-pipeline-list">
                <div>
                  <span>01</span>
                  <div>
                    <strong>Ingestion</strong>
                    <p>Validate and parse your BOM file.</p>
                  </div>
                </div>
                <div>
                  <span>02</span>
                  <div>
                    <strong>Component Intelligence</strong>
                    <p>Identify and enrich each component.</p>
                  </div>
                </div>
                <div>
                  <span>03</span>
                  <div>
                    <strong>Risk Analysis</strong>
                    <p>Evaluate procurement and lifecycle risk.</p>
                  </div>
                </div>
                <div>
                  <span>04</span>
                  <div>
                    <strong>Recommendations</strong>
                    <p>Generate alternatives and sourcing intelligence.</p>
                  </div>
                </div>
              </div>
            </article>
          </section>
        </div>
      </main>
    </div>
  );
}
