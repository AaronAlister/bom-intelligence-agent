import { useEffect, useState } from "react";

import type { BOMRisk, IngestionResult, RiskSeverity } from "../types/bom";

import type { WorkspaceView } from "../App";

type RiskIntelligenceProps = {
  ingestionResult: IngestionResult | null;
  onNavigate: (view: WorkspaceView) => void;
  onLogout: () => void;
};

function severityClass(severity: RiskSeverity): string {
  return `bi-risk-severity bi-risk-severity--${severity.toLowerCase()}`;
}

function formatScore(score: number): string {
  return Number.isInteger(score) ? String(score) : score.toFixed(2);
}

export default function RiskIntelligence({
  ingestionResult,
  onNavigate,
  onLogout,
}: RiskIntelligenceProps) {
  const [risk, setRisk] = useState<BOMRisk | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const bomDatabaseId = ingestionResult?.bom_database_id;

  const loadRisk = async () => {
    if (!bomDatabaseId) {
      setRisk(null);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/v1/boms/${bomDatabaseId}/risk`);

      if (response.status === 404) {
        setRisk(null);
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to load BOM risk: ${response.status}`);
      }

      const result = (await response.json()) as BOMRisk;

      setRisk(result);
    } catch (loadError) {
      console.error("Failed to load BOM risk:", loadError);

      setError("Unable to load the current BOM risk assessment.");
    } finally {
      setLoading(false);
    }
  };

  const analyzeRisk = async () => {
    if (!bomDatabaseId) {
      setError("No active BOM is available for risk analysis.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/v1/boms/${bomDatabaseId}/risk`, {
        method: "POST",
      });

      if (!response.ok) {
        let detail = `Risk analysis failed: ${response.status}`;

        try {
          const errorBody = (await response.json()) as {
            detail?: string;
          };

          if (errorBody.detail) {
            detail = errorBody.detail;
          }
        } catch {
          // Keep the default error message.
        }

        throw new Error(detail);
      }

      const result = (await response.json()) as BOMRisk;

      setRisk(result);
    } catch (analysisError) {
      console.error("Failed to analyze BOM risk:", analysisError);

      setError(
        analysisError instanceof Error
          ? analysisError.message
          : "BOM risk analysis failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRisk();
  }, [bomDatabaseId]);

  const navigationItems = [
    {
      label: "Dashboard",
      view: "dashboard" as WorkspaceView,
      icon: "▪",
    },
    {
      label: "BOM Analysis",
      view: "bom-analysis" as WorkspaceView,
      icon: "◈",
    },
    {
      label: "Components",
      view: "components" as WorkspaceView,
      icon: "◎",
    },
    {
      label: "Risk Intelligence",
      view: "risk" as WorkspaceView,
      icon: "△",
    },
    {
      label: "Alternatives",
      view: "alternatives" as WorkspaceView,
      icon: "⇄",
    },
    {
      label: "Lifecycle",
      view: "lifecycle" as WorkspaceView,
      icon: "◷",
    },
    {
      label: "Reports",
      view: "reports" as WorkspaceView,
      icon: "▥",
    },
  ];

  return (
    <div className="bi-dashboard">
      {/* =====================================================
          SIDEBAR
          ===================================================== */}

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
              const isActive = item.view === "risk";

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

      {/* =====================================================
          MAIN
          ===================================================== */}

      <main className="bi-main">
        <header className="bi-topbar">
          <div className="bi-breadcrumb">
            <span>Workspace</span>
            <b>/</b>
            <strong>Risk Intelligence</strong>
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
          {/* =================================================
              PAGE HEADER
              ================================================= */}

          <div className="bi-page-heading">
            <div>
              <span className="bi-eyebrow">ENGINEERING RISK</span>

              <h1>Risk Intelligence</h1>
            </div>

            <p>
              Assess component-level procurement and lifecycle risk across the
              active BOM.
            </p>
          </div>

          {/* =================================================
              NO ACTIVE BOM
              ================================================= */}

          {!ingestionResult && (
            <section className="bi-panel">
              <div className="bi-empty-state">
                <div className="bi-empty-icon" aria-hidden="true">
                  △
                </div>

                <h3>No active BOM</h3>

                <p>
                  Upload and analyze a BOM before running risk intelligence.
                </p>

                <button
                  className="sign-in-button"
                  type="button"
                  onClick={() => onNavigate("bom-analysis")}
                >
                  <span>Go to BOM Analysis</span>

                  <span>→</span>
                </button>
              </div>
            </section>
          )}

          {/* =================================================
              ACTIVE BOM
              ================================================= */}

          {ingestionResult && (
            <>
              <section className="bi-panel bi-risk-header-panel">
                <div className="bi-panel-header">
                  <div>
                    <div className="bi-panel-title">
                      <span aria-hidden="true">△</span>

                      <span>ACTIVE BOM</span>
                    </div>

                    <h2>{ingestionResult.source_file}</h2>

                    <p className="bi-risk-bom-meta">
                      {ingestionResult.components.length} components · BOM
                      database ID {ingestionResult.bom_database_id}
                    </p>
                  </div>

                  <button
                    className="bi-risk-analyze-button"
                    type="button"
                    onClick={() => {
                      void analyzeRisk();
                    }}
                    disabled={loading}
                  >
                    {loading ? "ANALYZING..." : "RUN RISK ANALYSIS"}
                  </button>
                </div>
              </section>

              {/* ERROR */}

              {error && (
                <div className="bi-risk-error" role="alert">
                  <span aria-hidden="true">!</span>

                  <span>{error}</span>
                </div>
              )}

              {/* LOADING */}

              {loading && !risk && (
                <section className="bi-panel">
                  <div className="bi-empty-state">
                    <div className="bi-loading-indicator" aria-hidden="true">
                      <span />
                      <span />
                      <span />
                    </div>

                    <h3>Running risk intelligence</h3>

                    <p>Assessing lifecycle, availability and component risk.</p>
                  </div>
                </section>
              )}

              {/* =================================================
                  RISK RESULTS
                  ================================================= */}

              {risk && !loading && (
                <>
                  {/* RISK OVERVIEW */}

                  <section
                    className="bi-risk-overview"
                    aria-label="BOM risk overview"
                  >
                    <article className="bi-risk-score-card">
                      <div className="bi-risk-card-label">
                        <span>BOM RISK SCORE</span>

                        <span className="bi-risk-card-icon">△</span>
                      </div>

                      <div className="bi-risk-score">
                        {formatScore(risk.overall_score)}

                        <span>/ 100</span>
                      </div>

                      <span className={severityClass(risk.severity)}>
                        {risk.severity}
                      </span>

                      <div className="bi-risk-progress">
                        <span
                          style={{
                            width: `${Math.min(
                              Math.max(risk.overall_score, 0),
                              100,
                            )}%`,
                          }}
                        />
                      </div>

                      <p>{risk.summary}</p>
                    </article>

                    <article className="bi-risk-stat-card">
                      <span>COMPONENTS ASSESSED</span>

                      <strong>{risk.component_count}</strong>

                      <small>Components with persisted risk data</small>
                    </article>

                    <article className="bi-risk-stat-card">
                      <span>HIGH RISK</span>

                      <strong
                        className={risk.high_risk_count > 0 ? "is-warning" : ""}
                      >
                        {risk.high_risk_count}
                      </strong>

                      <small>Components requiring attention</small>
                    </article>

                    <article className="bi-risk-stat-card">
                      <span>CRITICAL</span>

                      <strong
                        className={risk.critical_count > 0 ? "is-critical" : ""}
                      >
                        {risk.critical_count}
                      </strong>

                      <small>Immediate procurement concern</small>
                    </article>

                    <article className="bi-risk-stat-card">
                      <span>LIFECYCLE RISK</span>

                      <strong
                        className={
                          risk.lifecycle_risk_count > 0 ? "is-warning" : ""
                        }
                      >
                        {risk.lifecycle_risk_count}
                      </strong>

                      <small>Lifecycle-related exposure</small>
                    </article>

                    <article className="bi-risk-stat-card">
                      <span>AVAILABILITY RISK</span>

                      <strong
                        className={
                          risk.availability_risk_count > 0 ? "is-warning" : ""
                        }
                      >
                        {risk.availability_risk_count}
                      </strong>

                      <small>Supply-related exposure</small>
                    </article>
                  </section>

                  {/* =================================================
                      TOP COMPONENTS
                      ================================================= */}

                  <section className="bi-panel">
                    <div className="bi-panel-header">
                      <div>
                        <div className="bi-panel-title">
                          <span>COMPONENT RISK</span>
                        </div>

                        <h2>Top risk components</h2>

                        <p>
                          Highest-scoring components in the current BOM
                          assessment.
                        </p>
                      </div>

                      <span className="bi-component-count">
                        {risk.top_risk_components.length} TOP COMPONENTS
                      </span>
                    </div>

                    {risk.top_risk_components.length === 0 ? (
                      <div className="bi-components-empty">
                        <p>
                          No component risk records are currently available.
                        </p>
                      </div>
                    ) : (
                      <div className="bi-risk-table-wrapper">
                        <table className="bi-risk-table">
                          <thead>
                            <tr>
                              <th>MPN</th>
                              <th>QUANTITY</th>
                              <th>SCORE</th>
                              <th>SEVERITY</th>
                              <th>LIFECYCLE</th>
                              <th>AVAILABILITY</th>
                            </tr>
                          </thead>

                          <tbody>
                            {risk.top_risk_components.map((component) => (
                              <tr key={component.component_id}>
                                <td>
                                  <strong>{component.mpn}</strong>
                                </td>

                                <td>{component.quantity}</td>

                                <td>
                                  <span className="bi-risk-score-cell">
                                    {formatScore(component.score)}
                                  </span>
                                </td>

                                <td>
                                  <span
                                    className={severityClass(
                                      component.severity,
                                    )}
                                  >
                                    {component.severity}
                                  </span>
                                </td>

                                <td>
                                  <span
                                    className={
                                      component.lifecycle_risk
                                        ? "bi-risk-flag bi-risk-flag--high"
                                        : "bi-risk-flag bi-risk-flag--normal"
                                    }
                                  >
                                    {component.lifecycle_risk
                                      ? "HIGH"
                                      : "NORMAL"}
                                  </span>
                                </td>

                                <td>
                                  <span
                                    className={
                                      component.availability_risk
                                        ? "bi-risk-flag bi-risk-flag--high"
                                        : "bi-risk-flag bi-risk-flag--normal"
                                    }
                                  >
                                    {component.availability_risk
                                      ? "HIGH"
                                      : "NORMAL"}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </section>

                  {/* =================================================
                      DRIVERS + RECOMMENDATIONS
                      ================================================= */}

                  <section className="bi-risk-two-column">
                    <article className="bi-panel">
                      <div className="bi-panel-header">
                        <div>
                          <div className="bi-panel-title">
                            <span>RISK DRIVERS</span>
                          </div>

                          <h2>Why the BOM is at risk</h2>
                        </div>
                      </div>

                      {risk.risk_drivers.length === 0 ? (
                        <div className="bi-components-empty">
                          <div className="bi-success-icon">✓</div>

                          <p>No significant risk drivers identified.</p>
                        </div>
                      ) : (
                        <div className="bi-risk-list">
                          {risk.risk_drivers.map((driver, index) => (
                            <div
                              className="bi-risk-list-item"
                              key={`${driver.component_id}-${index}`}
                            >
                              <div>
                                <strong>{driver.mpn}</strong>

                                <p>{driver.reason}</p>
                              </div>

                              <div className="bi-risk-list-score">
                                <strong>{formatScore(driver.score)}</strong>

                                <span
                                  className={severityClass(driver.severity)}
                                >
                                  {driver.severity}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </article>

                    <article className="bi-panel">
                      <div className="bi-panel-header">
                        <div>
                          <div className="bi-panel-title">
                            <span>RECOMMENDATIONS</span>
                          </div>

                          <h2>Recommended actions</h2>
                        </div>
                      </div>

                      {risk.recommendations.length === 0 ? (
                        <div className="bi-components-empty">
                          <div className="bi-success-icon">✓</div>

                          <p>No recommendations generated.</p>
                        </div>
                      ) : (
                        <div className="bi-risk-list">
                          {risk.recommendations.map((recommendation, index) => (
                            <div
                              className="bi-risk-list-item"
                              key={`${recommendation.component_id ?? "bom"}-${index}`}
                            >
                              <div>
                                <strong>
                                  {recommendation.mpn ?? "BOM-wide"}
                                </strong>

                                <p>{recommendation.action}</p>

                                <small>{recommendation.reason}</small>
                              </div>

                              <span
                                className={severityClass(
                                  recommendation.priority,
                                )}
                              >
                                {recommendation.priority}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </article>
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
