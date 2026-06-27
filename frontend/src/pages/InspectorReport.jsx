import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { getInspectorReport } from "@/lib/api";
import WarningBanner from "@/components/WarningBanner";
import ExplainFinding from "@/components/ExplainFinding";
import { fmt } from "@/lib/format";
import { ArrowLeft, FileSearch, ShieldCheck, AlertTriangle, AlertOctagon, Info } from "lucide-react";
import { API } from "@/lib/api";

const SEVERITY_TONE = {
  critical: { color: "#EF4444", bg: "#7F1D1D", Icon: AlertOctagon, label: "CRITICAL" },
  warning:  { color: "#F59E0B", bg: "#78350F", Icon: AlertTriangle, label: "WARNING" },
  info:     { color: "#38BDF8", bg: "#0c4a6e", Icon: Info, label: "INFO" },
};

function ScoreGauge({ score, size = 180 }) {
  const r = size / 2 - 12;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const color = score >= 80 ? "#10B981" : score >= 60 ? "#F59E0B" : "#EF4444";
  return (
    <div className="relative inline-block" style={{ width: size, height: size }} data-testid="inspector-score-gauge">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#3f3f46" strokeWidth="3" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="3" fill="none"
                strokeDasharray={`${c * pct} ${c}`} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-mono text-4xl tabular-nums" style={{ color }}>{score}</div>
        <div className="st-data-label">SCORE / 100</div>
      </div>
    </div>
  );
}

function SubScore({ label, value }) {
  const color = value >= 90 ? "#10B981" : value >= 70 ? "#F59E0B" : "#EF4444";
  return (
    <div className="border border-[var(--st-border)] bg-[var(--st-panel-deep)] p-3" data-testid={`subscore-${label.toLowerCase()}`}>
      <div className="st-data-label">{label}</div>
      <div className="font-mono text-2xl mt-1" style={{ color }}>{value}</div>
      <div className="h-1 bg-[var(--st-border)] mt-2">
        <div className="h-full" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

export default function InspectorReport() {
  const { reportId } = useParams();
  const [report, setReport] = useState(null);

  useEffect(() => {
    getInspectorReport(reportId).then(setReport);
  }, [reportId]);

  if (!report) {
    return (
      <div className="max-w-[1600px] mx-auto px-6 py-12 text-center font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest">
        LOADING INSPECTOR REPORT…
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] mx-auto px-6 py-6" data-testid="inspector-page">
      <div className="flex items-center justify-between mb-4">
        <Link to={`/profiles/${report.profile_id}`}
              className="font-mono text-[10px] text-[var(--st-text-muted)] hover:text-[var(--st-accent)] uppercase tracking-widest flex items-center gap-2"
              data-testid="back-to-profile-from-inspector">
          <ArrowLeft className="w-3 h-3" /> Back to profile · {report.profile_name}
        </Link>
        <div className="font-mono text-[10px] text-[var(--st-text-muted)] uppercase tracking-widest">
          REPORT :: {report.report_id.slice(0, 8)}
        </div>
      </div>

      <Panel className="mb-4" testId="inspector-header">
        <div className="flex flex-col md:flex-row md:items-center gap-6">
          <ScoreGauge score={report.score} />
          <div className="flex-1">
            <div className="flex items-center gap-2 font-mono text-[10px] text-[var(--st-text-muted)] tracking-widest uppercase mb-2">
              <FileSearch className="w-3 h-3 text-[var(--st-accent)]" />
              TUNE INSPECTOR PRO
            </div>
            <h1 className="text-2xl font-medium tracking-tight text-[var(--st-text)]">
              {report.profile_name}
            </h1>
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-2">
              Generated {fmt.date(report.created_at)} · source generation #{report.source_generation_index + 1}
            </div>

            <div className="grid grid-cols-3 gap-3 mt-4 max-w-md">
              <div className="border border-[var(--st-danger)] bg-[#7F1D1D]/20 p-2">
                <div className="font-mono text-[10px] text-[var(--st-danger)] uppercase tracking-widest">CRITICAL</div>
                <div className="font-mono text-xl text-[var(--st-danger)] tabular-nums">{report.counts.critical}</div>
              </div>
              <div className="border border-[var(--st-warning)] bg-[#78350F]/20 p-2">
                <div className="font-mono text-[10px] text-[var(--st-warning)] uppercase tracking-widest">WARNING</div>
                <div className="font-mono text-xl text-[var(--st-warning)] tabular-nums">{report.counts.warning}</div>
              </div>
              <div className="border border-[var(--st-accent)] bg-[var(--st-accent-deep)]/15 p-2">
                <div className="font-mono text-[10px] text-[var(--st-accent)] uppercase tracking-widest">INFO</div>
                <div className="font-mono text-xl text-[var(--st-accent)] tabular-nums">{report.counts.info}</div>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <SubScore label="FUEL" value={report.subsystem_scores.fuel} />
        <SubScore label="IGNITION" value={report.subsystem_scores.ignition} />
        <SubScore label="BOOST" value={report.subsystem_scores.boost} />
        <SubScore label="SAFETY" value={report.subsystem_scores.safety} />
      </div>

      <Panel className="mb-4" testId="inspector-recommendations">
        <PanelHeader label="PRIORITIZED RECOMMENDATIONS" sub={`${report.recommendations.length} ITEMS`}
                     right={<ShieldCheck className="w-4 h-4 text-[var(--st-safe)]" />} />
        <ol className="space-y-2 text-sm text-[var(--st-text-secondary)] leading-relaxed list-decimal list-inside">
          {report.recommendations.map((r, i) => <li key={i}>{r}</li>)}
        </ol>
      </Panel>

      <Panel testId="inspector-findings">
        <PanelHeader label="FINDINGS" sub={`${report.findings.length} TOTAL`} />
        {report.findings.length === 0 ? (
          <WarningBanner level="safe" code="NO_FINDINGS" message="No issues detected by the audit engine." />
        ) : (
          <div className="space-y-3">
            {report.findings.map((f, i) => {
              const tone = SEVERITY_TONE[f.severity] || SEVERITY_TONE.info;
              const Icon = tone.Icon;
              return (
                <div key={i} className="border p-4"
                     style={{ borderColor: tone.color, background: `${tone.bg}1f` }}
                     data-testid={`finding-${f.code}`}>
                  <div className="flex items-start gap-3">
                    <Icon className="w-4 h-4 mt-1 shrink-0" style={{ color: tone.color }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1 flex-wrap">
                        <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: tone.color }}>
                          {tone.label}
                        </span>
                        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-text-muted)]">
                          {f.code}
                        </span>
                        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-text-muted)]">
                          · {f.subsystem}
                        </span>
                        <div className="ml-auto">
                          <ExplainFinding
                            finding={f}
                            profileName={report.profile_name}
                            engineMetadata={report.engine_metadata}
                            safetyEnvelope={report.safety_envelope}
                            apiBase={API}
                            testId={`explain-${f.code}`}
                          />
                        </div>
                      </div>
                      <div className="text-sm text-[var(--st-text)] mb-2">{f.message}</div>
                      {f.remediation && (
                        <div className="text-xs text-[var(--st-text-secondary)] italic border-l-2 border-[var(--st-border)] pl-3">
                          → {f.remediation}
                        </div>
                      )}
                      {f.cells && f.cells.length > 0 && (
                        <div className="mt-2 font-mono text-[10px] text-[var(--st-text-muted)]">
                          {f.cells.length} affected cell{f.cells.length !== 1 ? "s" : ""} · sample: {f.cells.slice(0, 8).map(([r, c]) => `[${r},${c}]`).join(" ")}
                          {f.cells.length > 8 && " …"}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
