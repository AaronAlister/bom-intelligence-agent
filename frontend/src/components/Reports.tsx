import { useEffect, useState } from "react";

import type { WorkspaceView } from "../App";
import type { BOMReport, IngestionResult, RiskSeverity } from "../types/bom";

type ReportsProps = {
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

function severityClass(severity: RiskSeverity): string {
  return `bi-risk-severity bi-risk-severity--${severity.toLowerCase()}`;
}

function formatScore(score: number): string {
  return Number.isInteger(score) ? String(score) : score.toFixed(2);
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

function riskLabel(severity: RiskSeverity): string {
  switch (severity) {
    case "CRITICAL":
      return "Critical";

    case "HIGH":
      return "High";

    case "MEDIUM":
      return "Medium";

    case "LOW":
      return "Low";

    default:
      return "Unknown";
  }
}

export default function Reports({
  ingestionResult,
  onNavigate,
  onLogout,
}: ReportsProps) {
  const [report, setReport] = useState<BOMReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const bomDatabaseId = ingestionResult?.bom_database_id;

  const loadReport = async () => {
    if (!bomDatabaseId) {
      setReport(null);
      setError("");

      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`/api/v1/boms/${bomDatabaseId}/report`);

      if (!response.ok) {
        let detail = `Failed to load report: ${response.status}`;

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

      const result = (await response.json()) as BOMReport;

      setReport(result);
    } catch (loadError) {
      console.error("Failed to load BOM report:", loadError);

      setReport(null);

      setError(
        loadError instanceof Error
          ? loadError.message
          : "Unable to load the BOM report.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadReport();
  }, [bomDatabaseId]);

  return (
    <div className="bi-dashboard">
      {/* =========================================================
          SIDEBAR
          ========================================================= */}

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
              const isActive = item.view === "reports";

              return (
                <button
                  key={item.view}
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

      {/* =========================================================
          MAIN WORKSPACE
          ========================================================= */}

      <main className="bi-main">
        {/* =======================================================
            TOP BAR
            ======================================================= */}

        <header className="bi-topbar">
          <div className="bi-breadcrumb">
            <span>Workspace</span>

            <b>/</b>

            <strong>Reports</strong>
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

        {/* =======================================================
            PAGE CONTENT
            ======================================================= */}

        <div className="bi-content">
          <div className="bi-page-heading">
            <div>
              <span className="bi-eyebrow">BOM REPORTING</span>

              <h1>Intelligence Report</h1>
            </div>

            <p>
              Consolidated engineering intelligence for risk, lifecycle and
              availability decisions.
            </p>
          </div>

          {/* =====================================================
              NO ACTIVE BOM
              ===================================================== */}

          {!bomDatabaseId && (
            <section className="bi-panel">
              <div className="bi-empty-state">
                <div className="bi-empty-icon" aria-hidden="true">
                  ▥
                </div>

                <h3>No active BOM</h3>

                <p>
                  Upload and analyze a BOM before generating an intelligence
                  report.
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

          {/* =====================================================
              LOADING
              ===================================================== */}

          {loading && !report && (
            <section className="bi-panel bi-report-loading-panel">
              <div className="bi-loading-indicator">
                <span />
                <span />
                <span />
              </div>

              <div>
                <strong>Generating intelligence report</strong>

                <span>
                  Aggregating BOM risk, lifecycle and availability intelligence.
                </span>
              </div>
            </section>
          )}

          {/* =====================================================
              ERROR
              ===================================================== */}

          {error && (
            <section className="bi-panel bi-report-error" role="alert">
              <div className="bi-panel-header">
                <div>
                  <span className="bi-eyebrow">REPORT ERROR</span>

                  <h2>Unable to load report</h2>

                  <p>{error}</p>
                </div>
              </div>

              <button
                type="button"
                className="bi-secondary-button"
                onClick={() => {
                  void loadReport();
                }}
              >
                TRY AGAIN
              </button>
            </section>
          )}

          {/* =====================================================
              REPORT
              ===================================================== */}

          {report && (
            <>
              {/* =================================================
                  ACTIVE BOM HEADER
                  ================================================= */}

              <section className="bi-panel bi-report-overview">
                <div className="bi-report-overview-header">
                  <div>
                    <div className="bi-panel-title">
                      <span aria-hidden="true">▥</span>

                      <span>ACTIVE BOM</span>
                    </div>

                    <h2>
                      {report.source_file ??
                        report.product ??
                        `BOM #${report.bom_id}`}
                    </h2>

                    <p>{report.product ?? "BOM intelligence assessment"}</p>
                  </div>

                  <span className={severityClass(report.severity)}>
                    {riskLabel(report.severity)}
                  </span>
                </div>

                <div className="bi-report-meta">
                  <span>BOM #{report.bom_id}</span>

                  {report.revision && <span>REV {report.revision}</span>}

                  {report.source_format && (
                    <span>{report.source_format.toUpperCase()}</span>
                  )}

                  <span>Generated {formatDate(report.generated_at)}</span>
                </div>
              </section>

              {/* =================================================
                  KPI GRID
                  ================================================= */}

              <section className="bi-report-kpi-grid">
                <article className="bi-report-kpi">
                  <span className="bi-eyebrow">OVERALL RISK</span>

                  <strong>{formatScore(report.overall_score)}</strong>

                  <small>{riskLabel(report.severity)} exposure</small>
                </article>

                <article className="bi-report-kpi">
                  <span className="bi-eyebrow">COMPONENTS</span>

                  <strong>{report.component_count}</strong>

                  <small>{report.total_quantity} total units</small>
                </article>

                <article className="bi-report-kpi">
                  <span className="bi-eyebrow">HIGH RISK</span>

                  <strong>{report.high_risk_count}</strong>

                  <small>{report.critical_count} critical</small>
                </article>

                <article className="bi-report-kpi">
                  <span className="bi-eyebrow">LIFECYCLE</span>

                  <strong>{report.lifecycle_risk_count}</strong>

                  <small>lifecycle risk components</small>
                </article>

                <article className="bi-report-kpi">
                  <span className="bi-eyebrow">AVAILABILITY</span>

                  <strong>{report.availability_risk_count}</strong>

                  <small>availability risks</small>
                </article>
              </section>

              {/* =================================================
                  EXECUTIVE ASSESSMENT
                  ================================================= */}

              <section className="bi-panel bi-report-summary">
                <div className="bi-panel-header">
                  <div>
                    <span className="bi-panel-title">EXECUTIVE ASSESSMENT</span>

                    <h2>Current BOM Assessment</h2>
                  </div>
                </div>

                <p className="bi-report-summary-text">{report.summary}</p>
              </section>

              {/* =================================================
                  LIFECYCLE + AVAILABILITY
                  ================================================= */}

              <section className="bi-report-two-column">
                <article className="bi-panel">
                  <div className="bi-panel-header">
                    <div>
                      <span className="bi-panel-title">
                        COMPONENT LIFECYCLE
                      </span>

                      <h2>Lifecycle Summary</h2>
                    </div>
                  </div>

                  <div className="bi-report-stat-list">
                    <div>
                      <span>Active</span>

                      <strong>{report.lifecycle.active_count}</strong>
                    </div>

                    <div>
                      <span>NRND</span>

                      <strong>{report.lifecycle.nrnd_count}</strong>
                    </div>

                    <div>
                      <span>EOL</span>

                      <strong>{report.lifecycle.eol_count}</strong>
                    </div>

                    <div>
                      <span>Obsolete</span>

                      <strong>{report.lifecycle.obsolete_count}</strong>
                    </div>

                    <div>
                      <span>Unknown</span>

                      <strong>{report.lifecycle.unknown_count}</strong>
                    </div>

                    <div>
                      <span>Lifecycle risk</span>

                      <strong>{report.lifecycle.lifecycle_risk_count}</strong>
                    </div>
                  </div>
                </article>

                <article className="bi-panel">
                  <div className="bi-panel-header">
                    <div>
                      <span className="bi-panel-title">
                        SUPPLY AVAILABILITY
                      </span>

                      <h2>Availability Summary</h2>
                    </div>
                  </div>

                  <div className="bi-report-stat-list">
                    <div>
                      <span>Risk components</span>

                      <strong>
                        {report.availability.availability_risk_count}
                      </strong>
                    </div>

                    <div>
                      <span>Availability known</span>

                      <strong>
                        {report.availability.components_with_availability}
                      </strong>
                    </div>

                    <div>
                      <span>Availability unknown</span>

                      <strong>
                        {report.availability.components_without_availability}
                      </strong>
                    </div>
                  </div>
                </article>
              </section>

              {/* =================================================
                  TOP RISK COMPONENTS
                  ================================================= */}

              <section className="bi-panel">
                <div className="bi-panel-header">
                  <div>
                    <span className="bi-panel-title">RISK REGISTER</span>

                    <h2>Top Risk Components</h2>

                    <p>
                      Components requiring the most attention from the current
                      assessment.
                    </p>
                  </div>

                  <span className="bi-component-count">
                    {report.top_risk_components.length} COMPONENTS
                  </span>
                </div>

                {report.top_risk_components.length === 0 ? (
                  <div className="bi-empty-state bi-empty-state--compact">
                    <h3>No component-level risks</h3>

                    <p>
                      No component-level risks were identified in the current
                      assessment.
                    </p>
                  </div>
                ) : (
                  <div className="bi-report-table-wrap">
                    <table className="bi-report-table">
                      <thead>
                        <tr>
                          <th>MPN</th>
                          <th>MANUFACTURER</th>
                          <th>QTY</th>
                          <th>SCORE</th>
                          <th>SEVERITY</th>
                          <th>DRIVERS</th>
                        </tr>
                      </thead>

                      <tbody>
                        {report.top_risk_components.map((component) => (
                          <tr key={component.component_id}>
                            <td>
                              <strong>{component.mpn}</strong>
                            </td>

                            <td>{component.manufacturer ?? "Unknown"}</td>

                            <td>{component.quantity}</td>

                            <td>{formatScore(component.score)}</td>

                            <td>
                              <span
                                className={severityClass(component.severity)}
                              >
                                {riskLabel(component.severity)}
                              </span>
                            </td>

                            <td>
                              <div className="bi-report-driver-tags">
                                {component.lifecycle_risk && (
                                  <span>LIFECYCLE</span>
                                )}

                                {component.availability_risk && (
                                  <span>AVAILABILITY</span>
                                )}

                                {!component.lifecycle_risk &&
                                  !component.availability_risk && (
                                    <span>GENERAL</span>
                                  )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {/* =================================================
                  RISK DRIVERS + RECOMMENDATIONS
                  ================================================= */}

              <section className="bi-report-two-column">
                <article className="bi-panel">
                  <div className="bi-panel-header">
                    <div>
                      <span className="bi-panel-title">EXPLAINABILITY</span>

                      <h2>Risk Drivers</h2>

                      <p>
                        Factors contributing to the current BOM risk assessment.
                      </p>
                    </div>
                  </div>

                  {report.risk_drivers.length === 0 ? (
                    <div className="bi-empty-state bi-empty-state--compact">
                      <h3>No additional risk drivers</h3>

                      <p>
                        No additional explainable risk drivers were generated.
                      </p>
                    </div>
                  ) : (
                    <div className="bi-report-list">
                      {report.risk_drivers.map((driver, index) => (
                        <div
                          className="bi-report-list-item"
                          key={`${driver.component_id}-${index}`}
                        >
                          <div>
                            <strong>{driver.mpn}</strong>

                            <p>{driver.reason}</p>
                          </div>

                          <span className={severityClass(driver.severity)}>
                            {formatScore(driver.score)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </article>

                <article className="bi-panel">
                  <div className="bi-panel-header">
                    <div>
                      <span className="bi-panel-title">ACTION PLAN</span>

                      <h2>Recommendations</h2>

                      <p>
                        Recommended actions based on the current intelligence.
                      </p>
                    </div>
                  </div>

                  {report.recommendations.length === 0 ? (
                    <div className="bi-empty-state bi-empty-state--compact">
                      <h3>No immediate actions</h3>

                      <p>No immediate recommendations were generated.</p>
                    </div>
                  ) : (
                    <div className="bi-report-list">
                      {report.recommendations.map((recommendation, index) => (
                        <div
                          className="bi-report-list-item"
                          key={`${recommendation.mpn ?? "general"}-${index}`}
                        >
                          <div>
                            <strong>{recommendation.action}</strong>

                            <p>{recommendation.reason}</p>

                            {recommendation.mpn && (
                              <small>{recommendation.mpn}</small>
                            )}
                          </div>

                          <span
                            className={severityClass(recommendation.priority)}
                          >
                            {riskLabel(recommendation.priority)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </article>
              </section>

              {/* =================================================
                  REPORT FOOTER
                  ================================================= */}

              <footer className="bi-report-footer">
                <span>BOM Intelligence Agent</span>

                <span>Report generated {formatDate(report.generated_at)}</span>

                <span>BOM #{report.bom_id}</span>
              </footer>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
