import React, { useEffect, useState } from "react";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { safetyEnvelope } from "@/lib/api";
import WarningBanner from "@/components/WarningBanner";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import { fmt } from "@/lib/format";
import { ArrowLeft, ArrowRight, Shield } from "lucide-react";

const RISK_COLOR = {
  low: "#10B981",
  moderate: "#F59E0B",
  high: "#EF4444",
  extreme: "#EF4444",
};

function RiskRow({ label, value, testId }) {
  const tone = RISK_COLOR[value] || "var(--st-text-muted)";
  return (
    <div className="flex items-center justify-between py-2 border-b border-[var(--st-border)] last:border-0" data-testid={testId}>
      <span className="st-data-label">{label}</span>
      <span className="font-mono text-xs uppercase tracking-widest" style={{ color: tone }}>{value}</span>
    </div>
  );
}

function MetricCard({ label, value, sub, tone = "default", testId }) {
  const borderClass = tone === "danger" ? "border-[var(--st-danger)]"
                    : tone === "warning" ? "border-[var(--st-warning)]"
                    : tone === "safe" ? "border-[var(--st-safe)]"
                    : "border-[var(--st-border)]";
  return (
    <div className={`border ${borderClass} bg-[var(--st-panel-deep)] p-3`} data-testid={testId}>
      <div className="st-data-label mb-1">{label}</div>
      <div className="font-mono text-xl tabular-nums">{value}</div>
      {sub && <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">{sub}</div>}
    </div>
  );
}

export default function SafetyStep({ intake, envelope, setEnvelope, onBack, onNext }) {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    safetyEnvelope(intake)
      .then((res) => { if (mounted) setEnvelope(res); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [intake]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="safety-step">
      <div className="lg:col-span-2 flex flex-col gap-4">
        <Panel testId="safety-summary-panel">
          <PanelHeader
            index={2}
            label="STEP 02 // SAFETY ENVELOPE"
            sub="COMPUTED FROM INTAKE"
            right={envelope ? <ConfidenceBadge value={envelope.confidence} label="ENVELOPE CONFIDENCE" testId="envelope-confidence-badge" /> : null}
          />
          {loading ? (
            <div className="text-center py-12 font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest" data-testid="envelope-loading">
              COMPUTING ENVELOPE…
            </div>
          ) : envelope ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <MetricCard label="AFR FLOOR" value={fmt.num(envelope.afr_min, 2)} sub="RICHEST ALLOWED"
                            tone="safe" testId="metric-afr-min" />
                <MetricCard label="AFR CEILING" value={fmt.num(envelope.afr_max, 2)} sub="LEANEST ALLOWED"
                            tone="safe" testId="metric-afr-max" />
                <MetricCard label="IGN CEILING" value={fmt.deg(envelope.ignition_ceiling)} sub="BTDC MAX"
                            tone="warning" testId="metric-ign-ceiling" />
                <MetricCard label="BOOST CEILING"
                            value={envelope.boost_ceiling_kpa ? fmt.kpa(envelope.boost_ceiling_kpa) : "N/A"}
                            sub={envelope.boost_ceiling_kpa ? "ABSOLUTE" : "NA ENGINE"}
                            tone={envelope.boost_ceiling_kpa ? "warning" : "default"}
                            testId="metric-boost-ceiling" />
                <MetricCard label="INJECTOR HEADROOM"
                            value={fmt.pct(envelope.injector_headroom_pct)}
                            sub="@ 85% DUTY"
                            tone={envelope.injector_headroom_pct < 5 ? "danger" : envelope.injector_headroom_pct < 15 ? "warning" : "safe"}
                            testId="metric-inj-headroom" />
                <MetricCard label="TORQUE BASELINE" value={`${envelope.torque_baseline_nm} Nm`} sub="EST. BMEP MODEL" testId="metric-torque" />
                <div className="border border-[var(--st-border)] bg-[var(--st-panel-deep)] p-3 col-span-2">
                  <div className="grid grid-cols-2 gap-2">
                    <RiskRow label="KNOCK SENS." value={envelope.knock_sensitivity} testId="risk-knock" />
                    <RiskRow label="THERMAL RISK" value={envelope.thermal_risk} testId="risk-thermal" />
                  </div>
                </div>
              </div>

              <div className="space-y-2" data-testid="envelope-warnings">
                {envelope.warnings.length === 0 && (
                  <WarningBanner
                    level="safe"
                    code="ENVELOPE_CLEAN"
                    message="All checks pass within conservative limits. Generation will proceed without HP cap."
                  />
                )}
                {envelope.warnings.map((w, i) => (
                  <WarningBanner key={i} level={w.level} code={w.code} message={w.message} testId={`warning-${w.code}`} />
                ))}
              </div>
            </>
          ) : null}
        </Panel>

        <div className="flex items-center justify-between gap-3">
          <Button variant="ghost" onClick={onBack} data-testid="safety-back-btn"
                  className="rounded-none font-mono text-xs uppercase tracking-widest text-[var(--st-text-muted)] hover:text-[var(--st-text)]">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to intake
          </Button>
          <Button onClick={onNext} disabled={!envelope} data-testid="safety-next-btn"
                  className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs uppercase tracking-widest h-11 px-6">
            Generate Starter Maps <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <Panel raised testId="safety-explainer-panel">
          <PanelHeader label="HOW THE ENVELOPE WORKS" />
          <ul className="text-xs text-[var(--st-text-secondary)] space-y-2 leading-relaxed list-disc list-inside">
            <li><strong className="text-[var(--st-text)]">AFR floor & ceiling</strong> derive from stoichiometry of the chosen fuel; the floor protects against fouling, the ceiling against lean-knock.</li>
            <li><strong className="text-[var(--st-text)]">Ignition ceiling</strong> is a conservative MBT cap based on octane and compression ratio. Generated timing is clamped here.</li>
            <li><strong className="text-[var(--st-text)]">Boost ceiling</strong> respects intercooler class, fuel octane and compression. Higher only with race fuel and conservative CR.</li>
            <li><strong className="text-[var(--st-text)]">Injector headroom</strong> projects required fuel mass at target HP vs available flow at 85% duty.</li>
          </ul>
        </Panel>

        <Panel raised testId="safety-philosophy-panel">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-[var(--st-accent)] mt-1 shrink-0" />
            <div>
              <div className="st-panel-title mb-1">CONSERVATIVE BY DEFAULT</div>
              <p className="text-xs text-[var(--st-text-secondary)] leading-relaxed">
                The envelope is a hard limiter, not a suggestion. Every cell in the generated maps
                will respect these bounds. You can push closer to the limits in Step 4 — but never
                past them in a starter tune.
              </p>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
