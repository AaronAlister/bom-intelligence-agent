import { useEffect, useMemo, useState } from "react";

import type { IngestionResult } from "../types/bom";
import type { WorkspaceView } from "../App";

type LifecycleStatus = "ACTIVE" | "NRND" | "EOL" | "OBSOLETE" | "UNKNOWN";

type LifecycleRisk = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "UNKNOWN";

type LifecycleAssessment = {
  status: LifecycleStatus;
  eol_date: string | null;
  last_buy_date: string | null;
  risk: LifecycleRisk;
  source: string | null;
};

type LifecycleHistoryRecord = {
  id: number;
  component_id: number;
  status: LifecycleStatus;
  risk: LifecycleRisk;
  eol_date: string | null;
  last_buy_date: string | null;
  created_at: string;
};

type LifecycleHistoryResponse = {
  component_id: number;
  records: LifecycleHistoryRecord[];
};

type PersistedComponent = {
  id: number;
  mpn: string;
  manufacturer: string | null;
  description: string | null;
  category: string | null;
  package: string | null;
};

type ComponentListResponse = {
  components?: PersistedComponent[];
};

type LifecycleProps = {
  ingestionResult: IngestionResult | null;
  onNavigate: (view: WorkspaceView) => void;
  onLogout: () => void;
};

type NavigationItem = {
  label: string;
  view: WorkspaceView;
  icon: string;
};

const navigationItems: NavigationItem[] = [
  {
    label: "Dashboard",
    view: "dashboard",
    icon: "▪",
  },
  {
    label: "BOM Analysis",
    view: "bom-analysis",
    icon: "▤",
  },
  {
    label: "Components",
    view: "components",
    icon: "◇",
  },
  {
    label: "Risk Intelligence",
    view: "risk",
    icon: "△",
  },
  {
    label: "Alternatives",
    view: "alternatives",
    icon: "⇄",
  },
  {
    label: "Lifecycle",
    view: "lifecycle",
    icon: "◷",
  },
  {
    label: "Reports",
    view: "reports",
    icon: "▥",
  },
];

function statusClass(status: LifecycleStatus): string {
  return `bi-lifecycle-status bi-lifecycle-status--${status.toLowerCase()}`;
}

function riskClass(risk: LifecycleRisk): string {
  return `bi-lifecycle-risk bi-lifecycle-risk--${risk.toLowerCase()}`;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Not available";
  }

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function lifecycleDescription(status: LifecycleStatus): string {
  switch (status) {
    case "ACTIVE":
      return "Component is currently in active production.";

    case "NRND":
      return "Component is not recommended for new designs.";

    case "EOL":
      return "Component has reached end-of-life and requires procurement attention.";

    case "OBSOLETE":
      return "Component is obsolete and should be considered for replacement.";

    default:
      return "Lifecycle status could not be determined from available sources.";
  }
}

function riskDescription(risk: LifecycleRisk): string {
  switch (risk) {
    case "LOW":
      return "Low lifecycle exposure.";

    case "MEDIUM":
      return "Moderate lifecycle exposure.";

    case "HIGH":
      return "High lifecycle exposure. Procurement review is recommended.";

    case "CRITICAL":
      return "Critical lifecycle exposure. Replacement planning is recommended.";

    default:
      return "Lifecycle exposure could not be determined.";
  }
}

export default function Lifecycle({
  ingestionResult,
  onNavigate,
  onLogout,
}: LifecycleProps) {
  const [componentIndex, setComponentIndex] = useState(0);

  const [persistedComponentId, setPersistedComponentId] = useState<
    number | null
  >(null);

  const [lifecycle, setLifecycle] = useState<LifecycleAssessment | null>(null);

  const [history, setHistory] = useState<LifecycleHistoryResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [resolvingComponent, setResolvingComponent] = useState(false);
  const [error, setError] = useState("");

  const components = ingestionResult?.components ?? [];
  const selectedComponent = components[componentIndex];

  const selectedComponentLabel = useMemo(() => {
    if (!selectedComponent) {
      return "No component selected";
    }

    return selectedComponent.mpn;
  }, [selectedComponent]);

  /*
   * Resolve the persisted database component from the MPN.
   *
   * The ingestion payload and persisted component record are
   * separate representations. The MPN is the stable bridge
   * between them.
   */
  const resolvePersistedComponent = async (
    mpn: string,
  ): Promise<PersistedComponent> => {
    const response = await fetch(
      `/api/v1/components?search=${encodeURIComponent(
        mpn,
      )}&page=1&page_size=50`,
    );

    if (!response.ok) {
      throw new Error(`Failed to resolve component: ${response.status}`);
    }

    const result = (await response.json()) as ComponentListResponse;

    const persistedComponent = result.components?.find(
      (component) => component.mpn.toLowerCase() === mpn.toLowerCase(),
    );

    if (!persistedComponent) {
      throw new Error(`Persisted component "${mpn}" was not found.`);
    }

    return persistedComponent;
  };

  const loadLifecycle = async (
    componentId: number,
  ): Promise<LifecycleAssessment> => {
    const response = await fetch(`/api/v1/components/${componentId}/lifecycle`);

    if (!response.ok) {
      throw new Error(
        `Failed to load lifecycle intelligence: ${response.status}`,
      );
    }

    const result = (await response.json()) as LifecycleAssessment;

    setLifecycle(result);

    return result;
  };

  const loadHistory = async (
    componentId: number,
  ): Promise<LifecycleHistoryResponse | null> => {
    setHistoryLoading(true);

    try {
      const response = await fetch(
        `/api/v1/components/${componentId}/lifecycle/history`,
      );

      if (!response.ok) {
        if (response.status === 404) {
          setHistory(null);
          return null;
        }

        throw new Error(`Failed to load lifecycle history: ${response.status}`);
      }

      const result = (await response.json()) as LifecycleHistoryResponse;

      setHistory(result);

      return result;
    } catch (historyError) {
      console.error("Failed to load lifecycle history:", historyError);

      setHistory(null);

      return null;
    } finally {
      setHistoryLoading(false);
    }
  };

  const resolveSelectedComponent = async (): Promise<number> => {
    if (!selectedComponent) {
      throw new Error("No BOM component is available for lifecycle analysis.");
    }

    /*
     * Prefer the component ID already present in the ingestion
     * response when it is valid.
     */
    if (
      typeof selectedComponent.component_id === "number" &&
      selectedComponent.component_id > 0
    ) {
      setPersistedComponentId(selectedComponent.component_id);

      return selectedComponent.component_id;
    }

    /*
     * Fallback to the persisted component lookup by MPN.
     */
    const persistedComponent = await resolvePersistedComponent(
      selectedComponent.mpn,
    );

    setPersistedComponentId(persistedComponent.id);

    return persistedComponent.id;
  };

  useEffect(() => {
    setLifecycle(null);
    setHistory(null);
    setError("");
    setPersistedComponentId(null);

    if (!selectedComponent) {
      return;
    }

    let cancelled = false;

    const restoreLifecycle = async () => {
      setResolvingComponent(true);

      try {
        const componentId = await resolveSelectedComponent();

        if (cancelled) {
          return;
        }

        await Promise.all([
          loadLifecycle(componentId),
          loadHistory(componentId),
        ]);
      } catch (restoreError) {
        if (cancelled) {
          return;
        }

        console.error(
          "Failed to restore lifecycle intelligence:",
          restoreError,
        );

        setLifecycle(null);

        setError(
          restoreError instanceof Error
            ? restoreError.message
            : "Unable to load lifecycle intelligence.",
        );
      } finally {
        if (!cancelled) {
          setResolvingComponent(false);
        }
      }
    };

    void restoreLifecycle();

    return () => {
      cancelled = true;
    };
  }, [selectedComponent]);

  const runLifecycleAnalysis = async () => {
    if (!selectedComponent) {
      setError("No BOM component is available for lifecycle analysis.");

      return;
    }

    setLoading(true);
    setError("");

    try {
      const componentId = await resolveSelectedComponent();

      await Promise.all([loadLifecycle(componentId), loadHistory(componentId)]);
    } catch (analysisError) {
      console.error("Lifecycle analysis failed:", analysisError);

      setLifecycle(null);

      setError(
        analysisError instanceof Error
          ? analysisError.message
          : "Lifecycle analysis failed.",
      );
    } finally {
      setLoading(false);
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
            {navigationItems.map((item) => {
              const isActive = item.view === "lifecycle";

              return (
                <button
                  key={item.label}
                  className={`bi-nav-item ${isActive ? "active" : ""}`}
                  type="button"
                  onClick={() => onNavigate(item.view)}
                  aria-current={isActive ? "page" : undefined}
                >
                  <span className="bi-nav-icon" aria-hidden="true">
                    {item.icon}
                  </span>

                  <span>{item.label}</span>
                </button>
              );
            })}
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
            <strong>Lifecycle</strong>
          </div>

          <div className="bi-topbar-actions">
            <div className="bi-live-status">
              <span className="bi-live-dot" />
              <span>LIVE</span>
            </div>

            <button
              className="bi-icon-button"
              type="button"
              aria-label="Notifications"
            >
              ♧<span className="bi-notification-badge">0</span>
            </button>

            <div className="bi-avatar" aria-label="Account">
              AA
            </div>
          </div>
        </header>

        <div className="bi-content">
          <div className="bi-page-heading">
            <div>
              <span className="bi-eyebrow">COMPONENT LIFECYCLE</span>

              <h1>Lifecycle Intelligence</h1>
            </div>

            <p>
              Monitor component lifecycle status, risk and end-of-life exposure
              across the active BOM.
            </p>
          </div>

          {!ingestionResult && (
            <section className="bi-panel">
              <div className="bi-empty-state">
                <div className="bi-empty-icon" aria-hidden="true">
                  ◷
                </div>

                <h3>No active BOM</h3>

                <p>
                  Upload and analyze a BOM before viewing lifecycle
                  intelligence.
                </p>

                <button
                  className="bi-primary-button"
                  type="button"
                  onClick={() => onNavigate("bom-analysis")}
                >
                  <span>Go to BOM Analysis</span>

                  <span>→</span>
                </button>
              </div>
            </section>
          )}

          {ingestionResult && (
            <>
              {/* =====================================================
                  ACTIVE BOM
                  ===================================================== */}

              <section className="bi-panel bi-lifecycle-header-panel">
                <div className="bi-lifecycle-bom-header">
                  <div>
                    <div className="bi-panel-title">
                      <span aria-hidden="true">◇</span>

                      <span>ACTIVE BOM</span>
                    </div>

                    <h2>{ingestionResult.source_file}</h2>

                    <p className="bi-lifecycle-bom-meta">
                      {components.length} components
                      {" · "}
                      BOM database ID {ingestionResult.bom_database_id}
                    </p>
                  </div>

                  <div className="bi-lifecycle-bom-stats">
                    <div>
                      <span>VALID ROWS</span>

                      <strong>{ingestionResult.valid_rows}</strong>
                    </div>

                    <div>
                      <span>FORMAT</span>

                      <strong>
                        {ingestionResult.source_format.toUpperCase()}
                      </strong>
                    </div>
                  </div>
                </div>
              </section>

              {/* =====================================================
                  COMPONENT SELECTION
                  ===================================================== */}

              <section className="bi-panel bi-lifecycle-target-panel">
                <div className="bi-panel-header">
                  <div>
                    <div className="bi-panel-title">
                      <span>COMPONENT SELECTION</span>
                    </div>

                    <h2>Lifecycle target</h2>

                    <p>
                      Select a component from the active BOM to inspect its
                      lifecycle status.
                    </p>
                  </div>

                  <button
                    className="bi-primary-button bi-lifecycle-refresh"
                    type="button"
                    onClick={() => {
                      void runLifecycleAnalysis();
                    }}
                    disabled={
                      loading || resolvingComponent || !selectedComponent
                    }
                  >
                    {loading || resolvingComponent
                      ? "ANALYZING..."
                      : "REFRESH ANALYSIS"}
                  </button>
                </div>

                {components.length > 0 ? (
                  <div className="bi-lifecycle-selector">
                    <label htmlFor="lifecycle-component">COMPONENT</label>

                    <select
                      id="lifecycle-component"
                      value={componentIndex}
                      onChange={(event) =>
                        setComponentIndex(Number(event.target.value))
                      }
                    >
                      {components.map((component, index) => (
                        <option key={`${component.mpn}-${index}`} value={index}>
                          {component.mpn}
                          {component.manufacturer
                            ? ` · ${component.manufacturer}`
                            : ""}
                        </option>
                      ))}
                    </select>

                    {selectedComponent && (
                      <div className="bi-lifecycle-component-meta">
                        <span>
                          CATEGORY: {selectedComponent.category ?? "Unknown"}
                        </span>

                        <span>
                          PACKAGE: {selectedComponent.package ?? "Unknown"}
                        </span>

                        <span>QTY: {selectedComponent.quantity}</span>

                        {persistedComponentId !== null && (
                          <span>COMPONENT ID: {persistedComponentId}</span>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bi-empty-state bi-empty-state--compact">
                    <h3>No components available</h3>

                    <p>
                      The active BOM does not contain any components to analyze.
                    </p>
                  </div>
                )}
              </section>

              {/* =====================================================
                  ERROR
                  ===================================================== */}

              {error && (
                <div className="bi-lifecycle-error" role="alert">
                  <span className="bi-lifecycle-error-icon" aria-hidden="true">
                    !
                  </span>

                  <div>
                    <strong>Lifecycle analysis unavailable</strong>

                    <span>{error}</span>
                  </div>
                </div>
              )}

              {/* =====================================================
                  LOADING
                  ===================================================== */}

              {(loading || resolvingComponent) && !lifecycle && (
                <section className="bi-panel bi-lifecycle-loading">
                  <div className="bi-loading-indicator">
                    <span />
                    <span />
                    <span />
                  </div>

                  <div>
                    <strong>Running lifecycle intelligence</strong>

                    <span>
                      Checking lifecycle information for{" "}
                      {selectedComponentLabel}.
                    </span>
                  </div>
                </section>
              )}

              {/* =====================================================
                  LIFECYCLE OVERVIEW
                  ===================================================== */}

              {lifecycle && !loading && (
                <>
                  <section
                    className="bi-lifecycle-overview"
                    aria-label="Lifecycle assessment"
                  >
                    <article className="bi-panel bi-lifecycle-status-card">
                      <div className="bi-lifecycle-card-label">
                        <span>LIFECYCLE STATUS</span>

                        <span
                          className="bi-lifecycle-card-icon"
                          aria-hidden="true"
                        >
                          ◷
                        </span>
                      </div>

                      <strong className={statusClass(lifecycle.status)}>
                        {lifecycle.status}
                      </strong>

                      <p>{lifecycleDescription(lifecycle.status)}</p>
                    </article>

                    <article className="bi-panel bi-lifecycle-stat-card">
                      <span>LIFECYCLE RISK</span>

                      <strong className={riskClass(lifecycle.risk)}>
                        {lifecycle.risk}
                      </strong>

                      <small>{riskDescription(lifecycle.risk)}</small>
                    </article>

                    <article className="bi-panel bi-lifecycle-stat-card">
                      <span>EOL DATE</span>

                      <strong>{formatDate(lifecycle.eol_date)}</strong>

                      <small>Manufacturer/distributor end-of-life date</small>
                    </article>

                    <article className="bi-panel bi-lifecycle-stat-card">
                      <span>LAST BUY DATE</span>

                      <strong>{formatDate(lifecycle.last_buy_date)}</strong>

                      <small>Final procurement opportunity</small>
                    </article>
                  </section>

                  {/* =================================================
                      COMPONENT INTELLIGENCE
                      ================================================= */}

                  <section className="bi-panel bi-lifecycle-details-panel">
                    <div className="bi-panel-header">
                      <div>
                        <div className="bi-panel-title">
                          <span>COMPONENT INTELLIGENCE</span>
                        </div>

                        <h2>{selectedComponentLabel}</h2>

                        <p>
                          Component metadata and intelligence source for the
                          current lifecycle assessment.
                        </p>
                      </div>

                      <span className={statusClass(lifecycle.status)}>
                        {lifecycle.status}
                      </span>
                    </div>

                    <div className="bi-lifecycle-details-grid">
                      <div>
                        <span>MANUFACTURER</span>

                        <strong>
                          {selectedComponent?.manufacturer ?? "Not available"}
                        </strong>
                      </div>

                      <div>
                        <span>CATEGORY</span>

                        <strong>
                          {selectedComponent?.category ?? "Not available"}
                        </strong>
                      </div>

                      <div>
                        <span>PACKAGE</span>

                        <strong>
                          {selectedComponent?.package ?? "Not available"}
                        </strong>
                      </div>

                      <div>
                        <span>INTELLIGENCE SOURCE</span>

                        <strong>{lifecycle.source ?? "Not available"}</strong>
                      </div>
                    </div>
                  </section>

                  {/* =================================================
                      LIFECYCLE HISTORY
                      ================================================= */}

                  <section className="bi-panel bi-lifecycle-history-panel">
                    <div className="bi-panel-header">
                      <div>
                        <div className="bi-panel-title">
                          <span aria-hidden="true">◷</span>

                          <span>LIFECYCLE HISTORY</span>
                        </div>

                        <h2>Historical lifecycle assessments</h2>

                        <p>Persisted lifecycle snapshots for this component.</p>
                      </div>

                      <span className="bi-component-count">
                        {history?.records.length ?? 0} SAVED
                      </span>
                    </div>

                    {historyLoading ? (
                      <div className="bi-lifecycle-history-loading">
                        Loading lifecycle history...
                      </div>
                    ) : history && history.records.length > 0 ? (
                      <div className="bi-lifecycle-history-list">
                        {history.records.slice(0, 5).map((record) => (
                          <article
                            className="bi-lifecycle-history-item"
                            key={record.id}
                          >
                            <div>
                              <span>ASSESSMENT</span>

                              <strong>#{record.id}</strong>

                              <small>{formatDateTime(record.created_at)}</small>
                            </div>

                            <div>
                              <span>STATUS</span>

                              <strong className={statusClass(record.status)}>
                                {record.status}
                              </strong>
                            </div>

                            <div>
                              <span>RISK</span>

                              <strong className={riskClass(record.risk)}>
                                {record.risk}
                              </strong>
                            </div>

                            <div>
                              <span>EOL</span>

                              <strong>{formatDate(record.eol_date)}</strong>
                            </div>

                            <div>
                              <span>LAST BUY</span>

                              <strong>
                                {formatDate(record.last_buy_date)}
                              </strong>
                            </div>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <div className="bi-empty-state bi-empty-state--compact">
                        <span className="bi-eyebrow">NO HISTORY</span>

                        <h3>No saved lifecycle assessments</h3>

                        <p>
                          Lifecycle history will appear here when assessments
                          are persisted.
                        </p>
                      </div>
                    )}
                  </section>
                </>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
