import type { WorkspaceView } from "../App";
import type { IngestionResult } from "../types/bom";

type DashboardProps = {
  onLogout: () => void;
  view: WorkspaceView;
  onNavigate: (view: WorkspaceView) => void;
  ingestionResult: IngestionResult | null;
};

type NavigationItem = {
  label: string;
  icon: string;
};

type Stat = {
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "purple" | "yellow" | "green";
  icon: string;
};

const navigationItems: NavigationItem[] = [
  { label: "Dashboard", icon: "▦" },
  { label: "BOM Analysis", icon: "▤" },
  { label: "Components", icon: "◈" },
  { label: "Risk Intelligence", icon: "△" },
  { label: "Alternatives", icon: "⇄" },
  { label: "Lifecycle", icon: "◷" },
  { label: "Reports", icon: "▥" },
];

export default function Dashboard({
  onLogout,
  view,
  onNavigate,
  ingestionResult,
}: DashboardProps) {
  const componentCount = ingestionResult?.components.length ?? 0;

  const stats: Stat[] = [
    {
      label: "BOMs Analyzed",
      value: ingestionResult ? "1" : "0",
      detail: ingestionResult ? "Active BOM" : "No analysis yet",
      tone: "blue",
      icon: "▤",
    },
    {
      label: "Components",
      value: String(componentCount),
      detail: ingestionResult ? "Components ingested" : "Awaiting BOM",
      tone: "purple",
      icon: "◈",
    },
    {
      label: "High Risk Components",
      value: "0",
      detail: ingestionResult ? "Risk analysis pending" : "Awaiting analysis",
      tone: "yellow",
      icon: "△",
    },
    {
      label: "System Health",
      value: "100%",
      detail: "All services online",
      tone: "green",
      icon: "♢",
    },
  ];

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
              const viewMap: Record<string, WorkspaceView> = {
                Dashboard: "dashboard",
                "BOM Analysis": "bom-analysis",
                Components: "components",
                "Risk Intelligence": "risk",
                Alternatives: "alternatives",
                Lifecycle: "lifecycle",
                Reports: "reports",
              };

              const targetView = viewMap[item.label];
              const isActive = view === targetView;

              return (
                <button
                  key={item.label}
                  className={`bi-nav-item ${isActive ? "active" : ""}`}
                  type="button"
                  onClick={() => onNavigate(targetView)}
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
          MAIN
      ========================================================= */}

      <main className="bi-main">
        {/* TOPBAR */}

        <header className="bi-topbar">
          <div className="bi-breadcrumb">
            <span>Workspace</span>
            <b>/</b>
            <strong>Dashboard</strong>
          </div>

          <div className="bi-topbar-actions">
            <label className="bi-search">
              <span aria-hidden="true">⌕</span>

              <input
                type="search"
                placeholder="Search components, MPN, manufacturer..."
                aria-label="Search components"
              />

              <kbd>Ctrl /</kbd>
            </label>

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

        {/* CONTENT */}

        <div className="bi-content">
          {/* =======================================================
              PAGE INTRO
          ======================================================= */}

          <div className="bi-page-heading">
            <div>
              <span className="bi-eyebrow">ENGINEERING WORKSPACE</span>

              <h1>Dashboard</h1>
            </div>

            <p>
              Engineering intelligence for component risk, supply and lifecycle
              decisions.
            </p>
          </div>

          {/* =======================================================
              STATS
          ======================================================= */}

          <section className="bi-stats-grid" aria-label="Platform statistics">
            {stats.map((stat) => (
              <article className="bi-stat-card" key={stat.label}>
                <div className="bi-stat-top">
                  <span>{stat.label}</span>

                  <div
                    className={`bi-stat-icon ${stat.tone}`}
                    aria-hidden="true"
                  >
                    {stat.icon}
                  </div>
                </div>

                <strong>{stat.value}</strong>

                <div className="bi-stat-bottom">
                  <span>{stat.detail}</span>
                </div>
              </article>
            ))}
          </section>

          {/* =======================================================
              MAIN PANELS
          ======================================================= */}

          <section className="bi-main-grid">
            {/* ACTIVE ANALYSIS */}

            <article className="bi-panel bi-analysis-panel">
              <div className="bi-panel-header">
                <div>
                  <div className="bi-panel-title">
                    <span aria-hidden="true">▤</span>
                    <span>ACTIVE ANALYSIS</span>
                  </div>

                  <h2>{ingestionResult ? "Active BOM" : "No active BOM"}</h2>
                </div>

                <span className="bi-analysis-badge">
                  {ingestionResult ? "INGESTED" : "READY"}
                </span>
              </div>

              {ingestionResult ? (
                <div className="bi-active-bom">
                  <div className="bi-empty-icon" aria-hidden="true">
                    ▤
                  </div>

                  <h3>{ingestionResult.source_file}</h3>

                  <p>
                    BOM successfully ingested with{" "}
                    {ingestionResult.components.length} components ready for
                    intelligence analysis.
                  </p>

                  <div className="bi-analysis-metrics">
                    <div>
                      <strong>{ingestionResult.valid_rows}</strong>
                      <span>VALID ROWS</span>
                    </div>

                    <div>
                      <strong>{ingestionResult.components.length}</strong>
                      <span>COMPONENTS</span>
                    </div>

                    <div>
                      <strong>
                        {ingestionResult.source_format.toUpperCase()}
                      </strong>
                      <span>FORMAT</span>
                    </div>
                  </div>

                  <span className="bi-empty-note">
                    BOM ID: {ingestionResult.bom_id}
                  </span>
                </div>
              ) : (
                <div className="bi-empty-state">
                  <div className="bi-empty-icon" aria-hidden="true">
                    ▤
                  </div>

                  <h3>Start with a BOM.</h3>

                  <p>
                    Upload a bill of materials to begin component intelligence,
                    procurement risk and lifecycle analysis.
                  </p>

                  <span className="bi-empty-note">
                    Upload a BOM from the BOM Analysis workspace.
                  </span>
                </div>
              )}
            </article>

            {/* AI BRIEFING */}

            <article className="bi-panel bi-briefing-panel">
              <div className="bi-panel-header">
                <div>
                  <div className="bi-panel-title">
                    <span aria-hidden="true">◇</span>
                    <span>AGENTIC INTELLIGENCE</span>
                  </div>

                  <h2>AI Briefing</h2>
                </div>

                <span className="bi-ai-provider">CLAUDE</span>
              </div>

              <div className="bi-ai-empty">
                <span className="bi-eyebrow">CURRENT ASSESSMENT</span>

                <h3>
                  {ingestionResult
                    ? "BOM ingestion complete"
                    : "No intelligence available"}
                </h3>

                <p>
                  {ingestionResult
                    ? `BOM ${ingestionResult.bom_id} is ready for risk, procurement, alternatives and lifecycle intelligence.`
                    : "Analyze a BOM to generate risk, procurement, alternatives and lifecycle intelligence."}
                </p>
              </div>

              <div className="bi-ai-summary">
                <div>
                  <span>Recommendations</span>
                  <strong>0</strong>
                </div>

                <div>
                  <span>Alternatives Found</span>
                  <strong>0</strong>
                </div>
              </div>
            </article>
          </section>

          {/* =======================================================
              COMPONENT INTELLIGENCE
          ======================================================= */}

          <section className="bi-panel bi-components-panel">
            <div className="bi-panel-header">
              <div>
                <div className="bi-panel-title">
                  <span aria-hidden="true">◈</span>
                  <span>COMPONENT INTELLIGENCE</span>
                </div>

                <h2>
                  {ingestionResult
                    ? `${ingestionResult.components.length} components ingested`
                    : "No components yet"}
                </h2>
              </div>

              <span className="bi-component-count">
                {ingestionResult?.components.length ?? 0} components
              </span>
            </div>

            <div className="bi-components-empty">
              <p>
                {ingestionResult
                  ? `The active BOM contains ${ingestionResult.components.length} ingested components.`
                  : "Upload and analyze a BOM to populate component, risk and procurement intelligence."}
              </p>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
