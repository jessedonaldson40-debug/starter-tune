import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import "@/App.css";
import { Toaster } from "@/components/ui/sonner";
import Dashboard from "@/pages/Dashboard";
import Wizard from "@/pages/Wizard";
import ProfileDetail from "@/pages/ProfileDetail";
import CompareView from "@/pages/CompareView";
import DiagSimSession from "@/pages/DiagSimSession";
import InspectorReport from "@/pages/InspectorReport";

const NAV_ITEMS = [
  { to: "/", label: "OVERVIEW", testId: "nav-overview" },
  { to: "/wizard", label: "GENERATE STARTER TUNE", testId: "nav-wizard", emphasis: true },
];

function TopBar() {
  const { pathname } = useLocation();
  useEffect(() => { document.title = "StandAIlone — Starter Tune Engine"; }, []);

  return (
    <header className="border-b border-[var(--st-border)] bg-[var(--st-panel-deep)]" data-testid="top-bar">
      <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center justify-between gap-6">
        <Link to="/" className="flex items-center gap-3 group" data-testid="brand-home-link">
          <div className="w-2 h-6 bg-[var(--st-accent)]" />
          <div className="flex flex-col leading-none">
            <span className="font-mono text-[10px] tracking-[0.22em] text-[var(--st-text-muted)]">
              STANDAILONE
            </span>
            <span className="text-sm font-medium tracking-tight text-[var(--st-text)]">
              STARTER TUNE ENGINE
            </span>
          </div>
        </Link>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.to || (item.to === "/wizard" && pathname.startsWith("/wizard"));
            return (
              <Link
                key={item.to}
                to={item.to}
                data-testid={item.testId}
                className={[
                  "font-mono text-[11px] tracking-[0.15em] px-3 py-2 border transition-colors",
                  item.emphasis
                    ? "border-[var(--st-accent)] text-[var(--st-accent)] hover:bg-[var(--st-accent-deep)]/30"
                    : active
                      ? "border-[var(--st-border-strong)] text-[var(--st-text)] bg-[var(--st-panel)]"
                      : "border-transparent text-[var(--st-text-secondary)] hover:text-[var(--st-text)]"
                ].join(" ")}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-3 font-mono text-[10px] uppercase text-[var(--st-text-muted)]">
          <span className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[var(--st-safe)] rounded-full" />
            ENGINE ONLINE
          </span>
          <span className="hidden md:inline">v1.0.0</span>
        </div>
      </div>
    </header>
  );
}

function FooterBar() {
  return (
    <footer className="border-t border-[var(--st-border)] bg-[var(--st-panel-deep)] mt-12" data-testid="footer-bar">
      <div className="max-w-[1600px] mx-auto px-6 h-10 flex items-center justify-between text-[10px] font-mono uppercase text-[var(--st-text-muted)]">
        <span>STANDAILONE ECOSYSTEM // STARTER TUNE ENGINE</span>
        <span>CONSERVATIVE BY DESIGN // ALWAYS VALIDATE ON DYNO</span>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <div className="App st-grid-bg min-h-screen flex flex-col">
      <BrowserRouter>
        <TopBar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/wizard" element={<Wizard />} />
            <Route path="/profiles/:id" element={<ProfileDetail />} />
            <Route path="/profiles/:id/compare" element={<CompareView />} />
            <Route path="/diagsim/:sessionId" element={<DiagSimSession />} />
            <Route path="/inspector/:reportId" element={<InspectorReport />} />
          </Routes>
        </main>
        <FooterBar />
      </BrowserRouter>
      <Toaster theme="dark" position="bottom-right" />
    </div>
  );
}
