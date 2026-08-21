import { useEffect, useMemo, useState } from "react";

import type { IngestionResult } from "../types/bom";
import type { WorkspaceView } from "../App";

type AlternativeComponent = {
  mpn: string;
  manufacturer: string | null;
  description: string | null;
  category: string | null;
  package: string | null;
};

type AlternativeCandidate = {
  component: AlternativeComponent;
  compatibility_score: number;
  compatibility_status: string;
  category_match: boolean;
  package_match: boolean;
  manufacturer_match: boolean;
  lifecycle_score: number;
  availability_score: number;
  reasons: string[];
};

type AlternativeResponse = {
  source_mpn: string;
  candidates: AlternativeCandidate[];
  best_candidate: AlternativeCandidate | null;
};

type AlternativeHistoryRecord = {
  id: number;
  source_component_id: number;
  alternative_component_id: number;
  compatibility_score: number;
  category_match: boolean;
  package_match: boolean;
  manufacturer_match: boolean;
  lifecycle_score: number;
  availability_score: number;
  reasons: string[];
  created_at: string;
};

type AlternativeHistoryResponse = {
  source_component_id: number;
  records: AlternativeHistoryRecord[];
};

type PersistResponse = AlternativeResponse & {
  persisted_count: number;
};

type PersistedComponent = {
  id: number;
  mpn: string;
};

type ComponentListResponse = {
  components?: PersistedComponent[];
  total?: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
};

type AlternativesProps = {
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
    icon: "▦",
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

function scoreClass(score: number): string {
  if (score >= 80) {
    return "bi-alternative-score bi-alternative-score--high";
  }

  if (score >= 60) {
    return "bi-alternative-score bi-alternative-score--medium";
  }

  return "bi-alternative-score bi-alternative-score--low";
}

function matchClass(value: boolean): string {
  return value
    ? "bi-alternative-match bi-alternative-match--yes"
    : "bi-alternative-match bi-alternative-match--no";
}

function formatDate(value: string): string {
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

function clampScore(score: number): number {
  return Math.max(0, Math.min(100, score));
}

export default function Alternatives({
  ingestionResult,
  onNavigate,
  onLogout,
}: AlternativesProps) {
  const [componentIndex, setComponentIndex] = useState(0);

  const [analysis, setAnalysis] = useState<AlternativeResponse | null>(null);

  const [history, setHistory] = useState<AlternativeHistoryResponse | null>(
    null,
  );

  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedComponentId, setSelectedComponentId] = useState<number | null>(
    null,
  );

  const components = ingestionResult?.components ?? [];
  const selectedComponent = components[componentIndex];

  const bestScore = useMemo(() => {
    if (!analysis?.best_candidate) {
      return null;
    }

    return clampScore(analysis.best_candidate.compatibility_score);
  }, [analysis]);

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

  const loadHistory = async (
    componentId: number,
  ): Promise<AlternativeHistoryResponse | null> => {
    setHistoryLoading(true);

    try {
      const response = await fetch(
        `/api/v1/components/${componentId}/alternatives/history`,
      );

      if (!response.ok) {
        if (response.status === 404) {
          setHistory(null);
          return null;
        }

        throw new Error(
          `Failed to load alternative history: ${response.status}`,
        );
      }

      const result = (await response.json()) as AlternativeHistoryResponse;

      setHistory(result);

      return result;
    } catch (historyError) {
      console.error("Failed to load alternative history:", historyError);

      setHistory(null);

      return null;
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    setAnalysis(null);
    setError("");
    setSelectedComponentId(null);

    if (!selectedComponent) {
      setHistory(null);
      return;
    }

    let cancelled = false;

    const restoreHistory = async () => {
      try {
        const persistedComponent = await resolvePersistedComponent(
          selectedComponent.mpn,
        );

        if (cancelled) {
          return;
        }

        setSelectedComponentId(persistedComponent.id);

        await loadHistory(persistedComponent.id);
      } catch (restoreError) {
        if (!cancelled) {
          console.error("Failed to restore alternative history:", restoreError);

          setHistory(null);
        }
      }
    };

    void restoreHistory();

    return () => {
      cancelled = true;
    };
  }, [selectedComponent]);

  const runAnalysis = async () => {
    if (!selectedComponent) {
      setError("No BOM component is available for analysis.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const persistedComponent = await resolvePersistedComponent(
        selectedComponent.mpn,
      );

      setSelectedComponentId(persistedComponent.id);

      const response = await fetch(
        `/api/v1/components/${persistedComponent.id}/alternatives?limit=10`,
      );

      if (!response.ok) {
        throw new Error(`Alternative analysis failed: ${response.status}`);
      }

      const result = (await response.json()) as AlternativeResponse;

      setAnalysis(result);
    } catch (analysisError) {
      console.error("Alternative analysis failed:", analysisError);

      setError(
        analysisError instanceof Error
          ? analysisError.message
          : "Alternative analysis failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const persistAnalysis = async () => {
    if (!selectedComponent) {
      setError("No BOM component is available for analysis.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const persistedComponent = await resolvePersistedComponent(
        selectedComponent.mpn,
      );

      setSelectedComponentId(persistedComponent.id);

      const response = await fetch(
        `/api/v1/components/${persistedComponent.id}/alternatives/analyze?limit=10`,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new Error(`Alternative persistence failed: ${response.status}`);
      }

      const result = (await response.json()) as PersistResponse;

      setAnalysis(result);

      await loadHistory(persistedComponent.id);
    } catch (analysisError) {
      console.error("Alternative persistence failed:", analysisError);

      setError(
        analysisError instanceof Error
          ? analysisError.message
          : "Alternative persistence failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const renderCandidate = (candidate: AlternativeCandidate, index: number) => {
    const score = clampScore(candidate.compatibility_score);

    return (
      <article
        className={`bi-panel bi-alternative-card ${
          index === 0 ? "bi-alternative-card--best" : ""
        }`}
        key={`${candidate.component.mpn}-${index}`}
      >
        <div className="bi-alternative-card-header">
          <div className="bi-alternative-identity">
            {index === 0 && (
              <span className="bi-alternative-best-label">BEST MATCH</span>
            )}

            <h3>{candidate.component.mpn}</h3>

            <p>
              {candidate.component.manufacturer ?? "Manufacturer unavailable"}
            </p>
          </div>

          <div className={scoreClass(score)}>
            <strong>{score.toFixed(1)}</strong>
            <span>/ 100</span>
            <small>{candidate.compatibility_status}</small>
          </div>
        </div>

        <div className="bi-alternative-match-grid">
          <div className={matchClass(candidate.category_match)}>
            <span>Category</span>
            <strong>{candidate.category_match ? "MATCH" : "NO MATCH"}</strong>
          </div>

          <div className={matchClass(candidate.package_match)}>
            <span>Package</span>
            <strong>{candidate.package_match ? "MATCH" : "NO MATCH"}</strong>
          </div>

          <div className={matchClass(candidate.manufacturer_match)}>
            <span>Manufacturer</span>
            <strong>
              {candidate.manufacturer_match ? "MATCH" : "NO MATCH"}
            </strong>
          </div>
        </div>

        <div className="bi-alternative-score-grid">
          <div>
            <span>Lifecycle</span>

            <div className="bi-alternative-progress">
              <span
                style={{
                  width: `${clampScore(candidate.lifecycle_score)}%`,
                }}
              />
            </div>

            <strong>{candidate.lifecycle_score.toFixed(1)}</strong>
          </div>

          <div>
            <span>Availability</span>

            <div className="bi-alternative-progress">
              <span
                style={{
                  width: `${clampScore(candidate.availability_score)}%`,
                }}
              />
            </div>

            <strong>{candidate.availability_score.toFixed(1)}</strong>
          </div>
        </div>

        <div className="bi-alternative-details">
          <div>
            <span>CATEGORY</span>
            <strong>{candidate.component.category ?? "Unknown"}</strong>
          </div>

          <div>
            <span>PACKAGE</span>
            <strong>{candidate.component.package ?? "Unknown"}</strong>
          </div>

          <div>
            <span>DESCRIPTION</span>
            <strong>
              {candidate.component.description ?? "No description available"}
            </strong>
          </div>
        </div>

        <div className="bi-alternative-reasons">
          <span className="bi-eyebrow">ENGINEERING REASONS</span>

          <ul>
            {candidate.reasons.map((reason, reasonIndex) => (
              <li key={`${candidate.component.mpn}-reason-${reasonIndex}`}>
                {reason}
              </li>
            ))}
          </ul>
        </div>
      </article>
    );
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
            {navigationItems.map((item) => (
              <button
                className={`bi-nav-item ${
                  item.view === "alternatives" ? "active" : ""
                }`}
                key={item.view}
                type="button"
                onClick={() => onNavigate(item.view)}
              >
                <span className="bi-nav-icon" aria-hidden="true">
                  {item.icon}
                </span>

                <span>{item.label}</span>
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
            <strong>Alternatives</strong>
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
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
                <path d="M10 21h4" />
              </svg>

              <span>0</span>
            </button>

            <button className="bi-profile" type="button" aria-label="Account">
              <span>AA</span>
            </button>
          </div>
        </header>

        <div className="bi-content">
          <section className="bi-page-heading">
            <div>
              <span className="bi-eyebrow">SOURCING INTELLIGENCE</span>

              <h1>Alternative Components</h1>

              <p>
                Identify compatible replacement components using engineering and
                procurement intelligence.
              </p>
            </div>
          </section>

          {!ingestionResult ? (
            <section className="bi-panel bi-empty-state">
              <span className="bi-eyebrow">NO ACTIVE BOM</span>

              <h2>Upload a BOM to begin sourcing analysis</h2>

              <p>
                Upload or restore a BOM before analysing alternative components.
              </p>

              <button
                className="bi-primary-button"
                type="button"
                onClick={() => onNavigate("bom-analysis")}
              >
                Open BOM Analysis
              </button>
            </section>
          ) : (
            <>
              <section className="bi-panel bi-alternatives-bom-header">
                <div>
                  <span className="bi-panel-title">
                    <span aria-hidden="true">◇</span>
                    <span>ACTIVE BOM</span>
                  </span>

                  <h2>{ingestionResult.source_file}</h2>

                  <p>
                    {components.length} components
                    {" · "}
                    BOM database ID{" "}
                    {(
                      ingestionResult as IngestionResult & {
                        bom_database_id?: number;
                      }
                    ).bom_database_id ?? ingestionResult.bom_id}
                  </p>
                </div>

                <div className="bi-alternatives-bom-stats">
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
              </section>

              <section className="bi-alternatives-layout">
                <aside className="bi-panel bi-alternatives-selector">
                  <div className="bi-panel-header">
                    <div>
                      <div className="bi-panel-title">
                        <span aria-hidden="true">▤</span>
                        <span>COMPONENTS</span>
                      </div>

                      <h2>Select source component</h2>
                    </div>

                    <span className="bi-component-count">
                      {components.length}
                    </span>
                  </div>

                  <div className="bi-alternative-component-list">
                    {components.map((component, index) => {
                      const isActive = index === componentIndex;

                      return (
                        <button
                          type="button"
                          key={`${component.mpn}-${index}`}
                          className={`bi-alternative-component ${
                            isActive ? "active" : ""
                          }`}
                          onClick={() => {
                            setComponentIndex(index);
                            setAnalysis(null);
                            setError("");
                          }}
                        >
                          <span>
                            <strong>{component.mpn}</strong>

                            <small>
                              {component.manufacturer ??
                                "Manufacturer unavailable"}
                            </small>
                          </span>

                          <span className="bi-alternative-quantity">
                            ×{component.quantity}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </aside>

                <section className="bi-alternatives-main">
                  <section className="bi-panel bi-source-component">
                    <div>
                      <span className="bi-eyebrow">SOURCE COMPONENT</span>

                      <h2>
                        {selectedComponent?.mpn ?? "No component selected"}
                      </h2>

                      <p>
                        {selectedComponent?.manufacturer ??
                          "Manufacturer unavailable"}
                      </p>
                    </div>

                    <div className="bi-source-component-actions">
                      <button
                        className="bi-secondary-button"
                        type="button"
                        onClick={() => void runAnalysis()}
                        disabled={loading || !selectedComponent}
                      >
                        {loading ? "ANALYSING..." : "FIND ALTERNATIVES"}
                      </button>

                      <button
                        className="bi-primary-button"
                        type="button"
                        onClick={() => void persistAnalysis()}
                        disabled={loading || !selectedComponent}
                      >
                        {loading ? "SAVING..." : "SAVE ANALYSIS"}
                      </button>
                    </div>
                  </section>

                  {error && (
                    <div className="bi-error" role="alert">
                      <strong>Alternative analysis error</strong>

                      <span>{error}</span>
                    </div>
                  )}

                  {loading && (
                    <section className="bi-panel bi-alternative-state">
                      <span className="bi-eyebrow">RUNNING ANALYSIS</span>

                      <h2>Finding compatible alternatives</h2>

                      <p>
                        Comparing engineering compatibility, lifecycle exposure
                        and availability.
                      </p>

                      <div className="bi-loading-bar">
                        <span />
                      </div>
                    </section>
                  )}

                  {!loading && !analysis && selectedComponent && !error && (
                    <section className="bi-panel bi-alternative-state">
                      <span className="bi-eyebrow">READY FOR ANALYSIS</span>

                      <h2>Find compatible alternatives</h2>

                      <p>
                        Compare engineering compatibility, lifecycle exposure
                        and availability before selecting a replacement.
                      </p>

                      {historyLoading && (
                        <div className="bi-history-loading">
                          Checking persisted recommendation history...
                        </div>
                      )}

                      {!historyLoading &&
                        history &&
                        history.records.length > 0 && (
                          <div className="bi-history-banner">
                            <div>
                              <span className="bi-eyebrow">
                                HISTORY AVAILABLE
                              </span>

                              <strong>
                                {history.records.length} persisted
                                recommendation
                                {history.records.length === 1 ? "" : "s"}
                              </strong>

                              <small>
                                Latest saved analysis:{" "}
                                {formatDate(history.records[0].created_at)}
                              </small>
                            </div>

                            <button
                              className="bi-secondary-button"
                              type="button"
                              onClick={() => void runAnalysis()}
                            >
                              LOAD CURRENT RESULTS
                            </button>
                          </div>
                        )}
                    </section>
                  )}

                  {!loading && analysis && (
                    <>
                      <section className="bi-alternative-overview">
                        <article className="bi-panel bi-alternative-overview-card bi-alternative-overview-card--source">
                          <span className="bi-eyebrow">SOURCE</span>

                          <strong>{analysis.source_mpn}</strong>

                          <small>Component under evaluation</small>
                        </article>

                        <article className="bi-panel bi-alternative-overview-card">
                          <span className="bi-eyebrow">CANDIDATES</span>

                          <strong>{analysis.candidates.length}</strong>

                          <small>Compatible candidates found</small>
                        </article>

                        <article className="bi-panel bi-alternative-overview-card">
                          <span className="bi-eyebrow">BEST MATCH</span>

                          <strong>
                            {analysis.best_candidate?.component.mpn ?? "NONE"}
                          </strong>

                          <small>Highest compatibility score</small>
                        </article>

                        <article className="bi-panel bi-alternative-overview-card">
                          <span className="bi-eyebrow">COMPATIBILITY</span>

                          <strong>
                            {bestScore !== null ? bestScore.toFixed(1) : "N/A"}
                          </strong>

                          <small>/ 100</small>
                        </article>
                      </section>

                      <section className="bi-panel bi-alternatives-results-panel">
                        <div className="bi-panel-header">
                          <div>
                            <div className="bi-panel-title">
                              <span aria-hidden="true">⇄</span>

                              <span>ALTERNATIVE RANKING</span>
                            </div>

                            <h2>Compatible replacement candidates</h2>

                            <p>
                              Candidates are ranked using compatibility,
                              lifecycle and availability signals.
                            </p>
                          </div>

                          <span className="bi-component-count">
                            {analysis.candidates.length} RESULTS
                          </span>
                        </div>

                        {analysis.candidates.length === 0 ? (
                          <div className="bi-empty-state bi-empty-state--compact">
                            <span className="bi-eyebrow">NO MATCHES</span>

                            <h3>No compatible alternatives found</h3>

                            <p>
                              No suitable candidates were identified for this
                              component.
                            </p>
                          </div>
                        ) : (
                          <div className="bi-alternative-grid">
                            {analysis.candidates.map(renderCandidate)}
                          </div>
                        )}
                      </section>
                    </>
                  )}

                  {history && history.records.length > 0 && !loading && (
                    <section className="bi-panel bi-alternative-history-panel">
                      <div className="bi-panel-header">
                        <div>
                          <div className="bi-panel-title">
                            <span aria-hidden="true">◷</span>

                            <span>ANALYSIS HISTORY</span>
                          </div>

                          <h2>Persisted recommendation snapshots</h2>
                        </div>

                        <span className="bi-component-count">
                          {history.records.length} SAVED
                        </span>
                      </div>

                      <div className="bi-alternative-history-list">
                        {history.records.slice(0, 5).map((record) => (
                          <article
                            className="bi-alternative-history-item"
                            key={record.id}
                          >
                            <div>
                              <span className="bi-eyebrow">SAVED ANALYSIS</span>

                              <strong>Recommendation #{record.id}</strong>

                              <small>{formatDate(record.created_at)}</small>
                            </div>

                            <div>
                              <span>COMPATIBILITY</span>

                              <strong>
                                {record.compatibility_score.toFixed(1)}
                              </strong>
                            </div>

                            <div>
                              <span>CATEGORY</span>

                              <strong>
                                {record.category_match ? "MATCH" : "NO MATCH"}
                              </strong>
                            </div>

                            <div>
                              <span>PACKAGE</span>

                              <strong>
                                {record.package_match ? "MATCH" : "NO MATCH"}
                              </strong>
                            </div>

                            <div>
                              <span>MANUFACTURER</span>

                              <strong>
                                {record.manufacturer_match
                                  ? "MATCH"
                                  : "NO MATCH"}
                              </strong>
                            </div>
                          </article>
                        ))}
                      </div>
                    </section>
                  )}
                </section>
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
