import { useEffect, useState } from "react";

import type { WorkspaceView } from "../App";
import type { IngestionResult } from "../types/bom";

type ComponentRecord = {
  id: number;
  mpn: string;
  manufacturer: string | null;
  description: string | null;
  category: string | null;
  package: string | null;
  normalized_mpn: string | null;
  normalized_manufacturer: string | null;
  normalized_category: string | null;
  datasheet_url: string | null;
  manufacturer_part_url: string | null;
  enrichment_status: string;
  enriched_at: string | null;
  created_at: string;
};

type ComponentListResponse = {
  components: ComponentRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

type ComponentEnrichmentResponse = {
  component: ComponentRecord;
  status: string;
};

type ComponentsProps = {
  onNavigate: (view: WorkspaceView) => void;
  onLogout: () => void;
  activeBom: IngestionResult | null;
};

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "";
const PAGE_SIZE = 25;

const STATUS_OPTIONS = [
  { value: "", label: "ALL STATUS" },
  { value: "ENRICHED", label: "ENRICHED" },
  { value: "PENDING", label: "PENDING" },
  { value: "NOT_FOUND", label: "NOT FOUND" },
  { value: "FAILED", label: "FAILED" },
];

function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getStatusClass(status: string): string {
  return `component-status-${status.toLowerCase().replace(/_/g, "-")}`;
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "NOT_FOUND":
      return "NOT FOUND";
    case "ENRICHED":
      return "ENRICHED";
    case "PENDING":
      return "PENDING";
    case "FAILED":
      return "FAILED";
    case "ENRICHING":
      return "ENRICHING";
    default:
      return status;
  }
}

export default function Components({
  onNavigate,
  onLogout,
  activeBom,
}: ComponentsProps) {
  const [components, setComponents] = useState<ComponentRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedComponentId, setSelectedComponentId] = useState<number | null>(
    null,
  );

  const [enrichingComponentId, setEnrichingComponentId] = useState<
    number | null
  >(null);

  const [enrichmentError, setEnrichmentError] = useState("");

  const activeBomId = activeBom?.bom_id ?? null;

  useEffect(() => {
    if (!activeBomId) {
      setComponents([]);
      setTotal(0);
      setTotalPages(1);
      setLoading(false);
      setError("");
      return;
    }

    let cancelled = false;

    const loadComponents = async () => {
      setLoading(true);
      setError("");

      try {
        const params = new URLSearchParams({
          page: String(page),
          page_size: String(PAGE_SIZE),
          bom_id: activeBomId,
        });

        if (search.trim()) {
          params.set("search", search.trim());
        }

        if (status) {
          params.set("enrichment_status", status);
        }

        const response = await fetch(
          `${API_BASE_URL}/api/v1/components?${params.toString()}`,
        );

        if (!response.ok) {
          throw new Error(`Failed to load components: ${response.status}`);
        }

        const data = (await response.json()) as ComponentListResponse;

        if (cancelled) {
          return;
        }

        setComponents(data.components);
        setTotal(data.total);
        setTotalPages(Math.max(data.total_pages, 1));
      } catch (loadError: unknown) {
        if (cancelled) {
          return;
        }

        if (loadError instanceof Error) {
          setError(loadError.message);
        } else {
          setError("Unable to load components.");
        }

        setComponents([]);
        setTotal(0);
        setTotalPages(1);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadComponents();

    return () => {
      cancelled = true;
    };
  }, [activeBomId, page, search, status]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
    setSelectedComponentId(null);
  };

  const handleStatusChange = (value: string) => {
    setStatus(value);
    setPage(1);
    setSelectedComponentId(null);
  };

  const handleComponentClick = (componentId: number) => {
    setEnrichmentError("");
    setSelectedComponentId((current) =>
      current === componentId ? null : componentId,
    );
  };

  const handleEnrichComponent = async (component: ComponentRecord) => {
    if (enrichingComponentId !== null) {
      return;
    }

    setEnrichingComponentId(component.id);
    setEnrichmentError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/components/${component.id}/enrich`,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        let message = `Enrichment failed with status ${response.status}.`;

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
            }
          }
        } catch {
          // Keep the default error message.
        }

        throw new Error(message);
      }

      const data = (await response.json()) as ComponentEnrichmentResponse;

      setComponents((current) =>
        current.map((item) =>
          item.id === data.component.id ? data.component : item,
        ),
      );
    } catch (enrichError: unknown) {
      if (enrichError instanceof Error) {
        setEnrichmentError(enrichError.message);
      } else {
        setEnrichmentError("Unable to enrich component.");
      }
    } finally {
      setEnrichingComponentId(null);
    }
  };

  const selectedComponent =
    components.find((component) => component.id === selectedComponentId) ??
    null;

  const firstVisibleRow = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;

  const lastVisibleRow = total === 0 ? 0 : Math.min(page * PAGE_SIZE, total);

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
              ["Dashboard", "▪", "dashboard"],
              ["BOM Analysis", "◈", "bom-analysis"],
              ["Components", "◉", "components"],
              ["Risk Intelligence", "△", "risk"],
              ["Alternatives", "↔", "alternatives"],
              ["Lifecycle", "◷", "lifecycle"],
              ["Reports", "▣", "reports"],
            ].map(([label, icon, target]) => (
              <button
                key={label}
                className={`bi-nav-item ${
                  target === "components" ? "active" : ""
                }`}
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

          <button className="bi-logout-button" type="button" onClick={onLogout}>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="bi-main">
        <header className="bi-topbar">
          <div className="bi-breadcrumb">
            <span>WORKSPACE</span>
            <span>/</span>
            <strong>COMPONENTS</strong>
          </div>

          <button className="bi-profile" type="button" aria-label="Account">
            <span>AA</span>
          </button>
        </header>

        <div className="bi-content">
          <div className="bi-page-heading">
            <div>
              <span className="bi-eyebrow">COMPONENT INTELLIGENCE</span>

              <h1>Components</h1>
            </div>

            <p>
              Components from the active BOM, enriched with distributor
              intelligence.
            </p>
          </div>

          {/* ===== REPLACED ACTIVE BOM CARD ===== */}
          {activeBom && (
            <div className="components-bom-header-card">
              <div className="components-bom-meta">
                <span className="components-bom-meta-label">BOM ID</span>
                <span className="components-bom-id">
                  {activeBom.bom_id || "—"}
                </span>
              </div>

              <div className="components-bom-divider" />

              {/* Source */}
              <div className="components-bom-info">
                <div className="components-bom-content">
                  <span className="components-bom-label">SOURCE FILE</span>
                  <strong className="components-bom-source">
                    {activeBom.metadata?.source_file ||
                      activeBom.source_file ||
                      "—"}
                  </strong>

                  <div className="components-bom-meta components-bom-uploaded">
                    <span className="components-bom-meta-label">UPLOADED</span>
                    <span>
                      {activeBom.metadata?.ingested_at
                        ? new Date(
                            activeBom.metadata.ingested_at,
                          ).toLocaleString("en-IN", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="components-bom-divider" />

              {/* Component count */}
              <div className="components-bom-info components-bom-info--count">
                <div className="components-bom-content">
                  <span className="components-bom-label">TOTAL COMPONENTS</span>
                  <strong className="components-bom-count">
                    {activeBom.components?.length ?? 0}
                  </strong>
                  <span className="components-bom-count-label">
                    In this BOM
                  </span>
                </div>

                <div className="components-bom-icon components-bom-icon--count">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    aria-hidden="true"
                  >
                    <path d="M12 2 20 6.5v11L12 22 4 17.5v-11L12 2Z" />
                    <path d="m4 6.5 8 4.5 8-4.5" />
                    <path d="M12 11v11" />
                  </svg>
                </div>
              </div>
            </div>
          )}
          {/* ===== END REPLACED ACTIVE BOM CARD ===== */}

          {!activeBom && (
            <div className="components-state components-state-error">
              Upload a BOM in BOM Analysis before viewing components.
            </div>
          )}

          {activeBom && (
            <section className="bi-panel components-panel">
              <div className="components-toolbar">
                <div className="components-search">
                  <span aria-hidden="true" className="components-search-icon">
                    ⌕
                  </span>

                  <input
                    type="search"
                    value={search}
                    onChange={(event) => handleSearchChange(event.target.value)}
                    placeholder="Search MPN, manufacturer or component..."
                    aria-label="Search components"
                  />
                </div>

                <select
                  className="components-status-filter"
                  value={status}
                  onChange={(event) => handleStatusChange(event.target.value)}
                  aria-label="Filter by enrichment status"
                >
                  {STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="components-table">
                <div className="components-table-header">
                  <span aria-hidden="true" />
                  <span>COMPONENT</span>
                  <span>MANUFACTURER</span>
                  <span>CATEGORY</span>
                  <span>PACKAGE</span>
                  <span>STATUS</span>
                  <span>UPDATED</span>
                </div>

                {loading && (
                  <div className="components-state">Loading components...</div>
                )}

                {!loading && error && (
                  <div className="components-state components-state-error">
                    {error}
                  </div>
                )}

                {!loading && !error && components.length === 0 && (
                  <div className="components-state">
                    {search || status
                      ? "No components match the current filters."
                      : "No components were found in this BOM."}
                  </div>
                )}

                {!loading &&
                  !error &&
                  components.map((component) => {
                    const isExpanded = selectedComponentId === component.id;

                    const isEnriching = enrichingComponentId === component.id;

                    return (
                      <article
                        key={component.id}
                        className={`component-item ${
                          isExpanded ? "component-item-expanded" : ""
                        }`}
                      >
                        <button
                          type="button"
                          className="components-row"
                          onClick={() => handleComponentClick(component.id)}
                          aria-expanded={isExpanded}
                        >
                          <span
                            className="component-chevron"
                            aria-hidden="true"
                          >
                            {isExpanded ? "⌄" : "›"}
                          </span>

                          <div className="component-primary">
                            <strong>{component.mpn}</strong>

                            <span>
                              {component.description ??
                                "Description unavailable"}
                            </span>
                          </div>

                          <span>
                            {component.manufacturer ?? "Not available"}
                          </span>

                          <span>{component.category ?? "Not available"}</span>

                          <span>{component.package ?? "Not available"}</span>

                          <span>
                            <span
                              className={`component-status ${getStatusClass(
                                component.enrichment_status,
                              )}`}
                            >
                              <span className="component-status-dot" />

                              {getStatusLabel(component.enrichment_status)}
                            </span>
                          </span>

                          <span className="component-date">
                            {formatDate(
                              component.enriched_at ?? component.created_at,
                            )}
                          </span>
                        </button>

                        {isExpanded && (
                          <div className="component-expanded-panel">
                            <div className="component-detail-grid">
                              <div className="component-detail-description">
                                <span>DESCRIPTION</span>

                                <p>
                                  {component.description ??
                                    "Description unavailable"}
                                </p>

                                <div className="component-detail-information">
                                  <div className="component-detail-field">
                                    <span>CATEGORY</span>

                                    <strong>
                                      {component.category ?? "Not available"}
                                    </strong>
                                  </div>

                                  <div className="component-detail-field">
                                    <span>PACKAGE</span>

                                    <strong>
                                      {component.package ?? "Not available"}
                                    </strong>
                                  </div>

                                  <div className="component-detail-field">
                                    <span>NORMALIZED MPN</span>

                                    <strong>
                                      {component.normalized_mpn ??
                                        "Not available"}
                                    </strong>
                                  </div>

                                  <div className="component-detail-field">
                                    <span>NORMALIZED MANUFACTURER</span>

                                    <strong>
                                      {component.normalized_manufacturer ??
                                        "Not available"}
                                    </strong>
                                  </div>

                                  <div className="component-detail-field">
                                    <span>ENRICHMENT STATUS</span>

                                    <strong>
                                      {getStatusLabel(
                                        component.enrichment_status,
                                      )}
                                    </strong>
                                  </div>

                                  <div className="component-detail-field">
                                    <span>ENRICHED AT</span>

                                    <strong>
                                      {formatDate(component.enriched_at)}
                                    </strong>
                                  </div>
                                </div>
                              </div>

                              <div className="component-detail-actions">
                                <div className="component-detail-link-card">
                                  <span>DATASHEET</span>

                                  {component.datasheet_url ? (
                                    <a
                                      href={component.datasheet_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      onClick={(event) =>
                                        event.stopPropagation()
                                      }
                                    >
                                      View datasheet →
                                    </a>
                                  ) : (
                                    <strong>Not available</strong>
                                  )}
                                </div>

                                <div className="component-detail-link-card">
                                  <span>MANUFACTURER PART</span>

                                  {component.manufacturer_part_url ? (
                                    <a
                                      href={component.manufacturer_part_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      onClick={(event) =>
                                        event.stopPropagation()
                                      }
                                    >
                                      View manufacturer page →
                                    </a>
                                  ) : (
                                    <strong>Not available</strong>
                                  )}
                                </div>

                                {enrichmentError && (
                                  <div
                                    className="component-detail-error"
                                    role="alert"
                                  >
                                    {enrichmentError}
                                  </div>
                                )}

                                <button
                                  type="button"
                                  className="bi-primary-button component-enrich-button"
                                  disabled={isEnriching}
                                  onClick={(event) => {
                                    event.stopPropagation();

                                    void handleEnrichComponent(component);
                                  }}
                                >
                                  <span>
                                    {isEnriching
                                      ? "ENRICHING..."
                                      : component.enrichment_status ===
                                          "ENRICHED"
                                        ? "REFRESH ENRICHMENT"
                                        : component.enrichment_status ===
                                              "NOT_FOUND" ||
                                            component.enrichment_status ===
                                              "FAILED"
                                          ? "RETRY ENRICHMENT"
                                          : "ENRICH COMPONENT"}
                                  </span>

                                  <span aria-hidden="true">
                                    {isEnriching ? "..." : "→"}
                                  </span>
                                </button>
                              </div>
                            </div>
                          </div>
                        )}
                      </article>
                    );
                  })}
              </div>

              <div className="components-footer">
                <span>
                  {total === 0
                    ? "No components"
                    : `Showing ${firstVisibleRow}–${lastVisibleRow} of ${total}`}
                </span>

                <div className="components-pagination">
                  <button
                    type="button"
                    disabled={page <= 1 || loading}
                    onClick={() =>
                      setPage((current) => Math.max(1, current - 1))
                    }
                    aria-label="Previous page"
                  >
                    ←
                  </button>

                  <span>
                    Page {page} of {totalPages}
                  </span>

                  <button
                    type="button"
                    disabled={page >= totalPages || loading}
                    onClick={() =>
                      setPage((current) => Math.min(totalPages, current + 1))
                    }
                    aria-label="Next page"
                  >
                    →
                  </button>
                </div>
              </div>
            </section>
          )}

          {selectedComponent && (
            <span className="sr-only" aria-live="polite">
              Selected component {selectedComponent.mpn}
            </span>
          )}
        </div>
      </main>
    </div>
  );
}
