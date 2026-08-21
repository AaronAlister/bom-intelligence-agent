import { useEffect, useState } from "react";

import Dashboard from "./components/Dashboard";
import Logo from "./components/Logo";
import BOMAnalysis from "./components/BOMAnalysis";
import Components from "./components/Components";
import RiskIntelligence from "./components/RiskIntelligence";
import Alternatives from "./components/Alternatives";
import Lifecycle from "./components/Lifecycle";
import Reports from "./components/Reports"; // <-- NEW IMPORT

import type { IngestionResult } from "./types/bom";

type LoginForm = {
  email: string;
  password: string;
};

export type WorkspaceView =
  | "dashboard"
  | "bom-analysis"
  | "components"
  | "risk"
  | "alternatives"
  | "lifecycle"
  | "reports";

const ACTIVE_BOM_STORAGE_KEY = "bom-intelligence-active-bom";

export default function App() {
  const [authenticated, setAuthenticated] = useState(false);

  const [view, setView] = useState<WorkspaceView>("dashboard");

  const [activeBom, setActiveBom] = useState<IngestionResult | null>(null);

  /*
   * Restore the most recently active BOM from browser storage.
   *
   * This prevents the active BOM from disappearing when the user
   * navigates between workspace pages.
   */
  useEffect(() => {
    try {
      const storedBom = localStorage.getItem(ACTIVE_BOM_STORAGE_KEY);

      if (!storedBom) {
        return;
      }

      const parsedBom = JSON.parse(storedBom) as IngestionResult;

      if (
        parsedBom &&
        typeof parsedBom === "object" &&
        typeof parsedBom.bom_id === "string"
      ) {
        setActiveBom(parsedBom);
      }
    } catch (restoreError) {
      console.error(
        "Failed to restore active BOM from browser storage:",
        restoreError,
      );

      localStorage.removeItem(ACTIVE_BOM_STORAGE_KEY);
    }
  }, []);

  /*
   * Persist the active BOM whenever it changes.
   *
   * The backend remains the source of truth. localStorage is only
   * used to preserve the current workspace state across navigation
   * and browser refreshes.
   */
  useEffect(() => {
    if (activeBom === null) {
      localStorage.removeItem(ACTIVE_BOM_STORAGE_KEY);
      return;
    }

    try {
      localStorage.setItem(ACTIVE_BOM_STORAGE_KEY, JSON.stringify(activeBom));
    } catch (storageError) {
      console.error("Failed to persist active BOM:", storageError);
    }
  }, [activeBom]);

  /*
   * Restore the latest BOM from the backend when the user
   * authenticates.
   *
   * The backend is authoritative, while localStorage provides
   * immediate UI persistence.
   */
  useEffect(() => {
    if (!authenticated) {
      return;
    }

    let cancelled = false;

    const loadLatestBom = async () => {
      try {
        const response = await fetch("/api/v1/boms/latest");

        if (response.status === 404) {
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to load latest BOM: ${response.status}`);
        }

        const result = (await response.json()) as IngestionResult;

        if (cancelled) {
          return;
        }

        if (result && typeof result.bom_id === "string") {
          setActiveBom(result);
        }
      } catch (loadError) {
        console.error("Failed to restore latest BOM:", loadError);
      }
    };

    void loadLatestBom();

    return () => {
      cancelled = true;
    };
  }, [authenticated]);

  const [form, setForm] = useState<LoginForm>({
    email: "analyst@company.com",
    password: "demo",
  });

  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const handleInputChange = (field: keyof LoginForm, value: string) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));

    if (error) {
      setError("");
    }
  };

  const handleLogin = () => {
    if (!form.email.trim() || !form.password.trim()) {
      setError("Enter your email and password.");
      return;
    }

    setError("");
    setView("dashboard");
    setAuthenticated(true);
  };

  const handleLogout = () => {
    setAuthenticated(false);
    setView("dashboard");

    /*
     * Keep the active BOM in localStorage.
     *
     * Logging out should not destroy the persisted workspace
     * state. If the user logs back in, the latest BOM can be
     * restored from the backend.
     */
    setActiveBom(null);
  };

  const handleBomIngested = (result: IngestionResult) => {
    setActiveBom(result);
  };

  if (authenticated) {
    if (view === "bom-analysis") {
      return (
        <BOMAnalysis
          onNavigate={setView}
          onLogout={handleLogout}
          onIngested={handleBomIngested}
          ingestionResult={activeBom}
        />
      );
    }

    if (view === "components") {
      return (
        <Components
          onNavigate={setView}
          onLogout={handleLogout}
          activeBom={activeBom}
        />
      );
    }

    if (view === "risk") {
      return (
        <RiskIntelligence
          ingestionResult={activeBom}
          onNavigate={setView}
          onLogout={handleLogout}
        />
      );
    }

    if (view === "alternatives") {
      return (
        <Alternatives
          ingestionResult={activeBom}
          onNavigate={setView}
          onLogout={handleLogout}
        />
      );
    }

    // ---- New Reports block ----
    if (view === "reports") {
      return (
        <Reports
          ingestionResult={activeBom}
          onNavigate={setView}
          onLogout={handleLogout}
        />
      );
    }

    // ---- Lifecycle block ----
    if (view === "lifecycle") {
      return (
        <Lifecycle
          ingestionResult={activeBom}
          onNavigate={setView}
          onLogout={handleLogout}
        />
      );
    }

    return (
      <Dashboard
        onLogout={handleLogout}
        view={view}
        onNavigate={setView}
        ingestionResult={activeBom}
      />
    );
  }

  return (
    <main className="login-page">
      <div className="login-window">
        <section className="login-product">
          <div className="product-background-glow" />

          <div className="product-content">
            <Logo />

            <div className="product-introduction">
              <span className="eyebrow">ENGINEERING INTELLIGENCE</span>

              <p>
                AI-powered intelligence for component risk, procurement,
                alternatives and lifecycle decisions.
              </p>
            </div>

            <div className="engineering-visual" aria-hidden="true">
              <div className="visual-ring visual-ring--outer" />
              <div className="visual-ring visual-ring--middle" />
              <div className="visual-ring visual-ring--inner" />

              <div className="visual-core">
                <span />
              </div>

              <div className="visual-line visual-line--one" />
              <div className="visual-line visual-line--two" />
              <div className="visual-line visual-line--three" />
            </div>

            <div className="capabilities">
              <div className="capability">
                <span>01</span>

                <div>
                  <strong>BOM Intelligence</strong>

                  <p>Parse and understand engineering BOMs.</p>
                </div>
              </div>

              <div className="capability">
                <span>02</span>

                <div>
                  <strong>Risk Analysis</strong>

                  <p>Identify procurement and lifecycle risk.</p>
                </div>
              </div>

              <div className="capability">
                <span>03</span>

                <div>
                  <strong>Alternative Sourcing</strong>

                  <p>Discover compatible component options.</p>
                </div>
              </div>
            </div>
          </div>

          <footer className="product-footer">
            <div className="operational-status">
              <span className="status-dot" />
              ALL SYSTEMS OPERATIONAL
            </div>

            <span className="footer-divider">•</span>

            <span>API</span>
            <span>DB</span>
            <span>RAG</span>
            <span>WORKER</span>
          </footer>
        </section>

        <section className="login-form-panel">
          <div className="login-form-content">
            <div className="login-heading">
              <span className="eyebrow">SECURE WORKSPACE</span>

              <h1>Welcome back</h1>

              <p>Sign in to your workspace.</p>
            </div>

            <form
              className="login-form"
              onSubmit={(event) => {
                event.preventDefault();
                handleLogin();
              }}
            >
              <label className="form-field">
                <span>EMAIL ADDRESS</span>

                <input
                  type="email"
                  value={form.email}
                  onChange={(event) =>
                    handleInputChange("email", event.target.value)
                  }
                  autoComplete="email"
                  placeholder="analyst@company.com"
                />
              </label>

              <label className="form-field">
                <span>PASSWORD</span>

                <div className="password-input">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={form.password}
                    onChange={(event) =>
                      handleInputChange("password", event.target.value)
                    }
                    autoComplete="current-password"
                    placeholder="Enter your password"
                  />

                  <button
                    className="password-toggle"
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </label>

              <div className="login-options">
                <label className="remember-option">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(event) => setRememberMe(event.target.checked)}
                  />

                  <span>Remember me</span>
                </label>

                <button
                  className="forgot-button"
                  type="button"
                  onClick={() =>
                    setError("Password recovery is not configured yet.")
                  }
                >
                  Forgot password?
                </button>
              </div>

              {error && (
                <div className="login-error" role="alert">
                  {error}
                </div>
              )}

              <button className="sign-in-button" type="submit">
                <span>Sign in</span>
                <span>→</span>
              </button>
            </form>

            <div className="secure-footer">
              <span>◉ Secure authentication</span>

              <span>v1.0.0</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
