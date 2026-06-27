import React, { useEffect, useState } from "react";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { generateTune } from "@/lib/api";
import { Heatmap, HeatmapLegend } from "@/components/Heatmap";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import WarningBanner from "@/components/WarningBanner";
import { fmt } from "@/lib/format";
import { ArrowLeft, ArrowRight, RefreshCw } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, YAxis, XAxis, Tooltip as RTooltip } from "recharts";

const STAGES = [
  "Parsing engine spec",
  "Validating injector headroom",
  "Resolving safety envelope",
  "Computing VE curve",
  "Seeding AFR target table",
  "Building fuel base map",
  "Generating MBT-anchored ignition map",
  "Computing boost target table",
  "Building idle / cold-start tables",
  "Confidence scoring",
  "Tune package ready",
];

export default function GenerateStep({ intake, adjustments, tune, setTune, onBack, onNext }) {
  const [progressStage, setProgressStage] = useState(0);
  const [building, setBuilding] = useState(false);

  const run = async () => {
    setBuilding(true);
    setProgressStage(0);
    // Stream stages while the backend computes
    const stageTicker = setInterval(() => {
      setProgressStage((s) => Math.min(STAGES.length - 1, s + 1));
    }, 180);
    try {
      const res = await generateTune(intake, adjustments);
      clearInterval(stageTicker);
      setProgressStage(STAGES.length - 1);
      setTune(res);
    } catch (e) {
      clearInterval(stageTicker);
    } finally {
      setBuilding(false);
    }
  };

  useEffect(() => {
    if (!tune) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const boosted = intake.induction !== "NA";

  return (
    <div className="grid grid-cols-1 gap-4" data-testid="generate-step">
      <Panel testId="generate-header-panel">
        <PanelHeader
          index={3}
          label="STEP 03 // BASE MAP GENERATION"
          sub={tune ? "READY" : "BUILDING…"}
          right={
            <div className="flex items-center gap-3">
              {tune && <ConfidenceBadge value={tune.confidence.overall} label="OVERALL" testId="generate-overall-confidence" />}
              <Button variant="outline" size="sm" onClick={run} disabled={building}
                      data-testid="regenerate-btn"
                      className="rounded-none border-[var(--st-border)] hover:border-[var(--st-accent)] hover:text-[var(--st-accent)] font-mono text-[10px] uppercase tracking-widest h-8">
                <RefreshCw className={`w-3 h-3 mr-2 ${building ? "animate-spin" : ""}`} />
                Regenerate
              </Button>
            </div>
          }
        />

        {/* Progress strip */}
        <div className="bg-[var(--st-panel-deep)] border border-[var(--st-border)] p-4" data-testid="generate-progress">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-text-secondary)]">
              [{String(progressStage + 1).padStart(2, "0")}/{String(STAGES.length).padStart(2, "0")}] {STAGES[progressStage]}
            </span>
            <span className="font-mono text-[10px] text-[var(--st-text-muted)]">
              {building ? "RUNNING" : tune ? "COMPLETE" : "IDLE"}
            </span>
          </div>
          <div className="h-1.5 bg-[var(--st-bg)] border border-[var(--st-border)] relative overflow-hidden">
            {building ? (
              <div className="absolute inset-0 st-progress-stream opacity-70" />
            ) : (
              <div className="absolute inset-0 bg-[var(--st-accent)]"
                   style={{ width: `${((progressStage + 1) / STAGES.length) * 100}%` }} />
            )}
          </div>
        </div>
      </Panel>

      {tune && (
        <>
          {/* Headline summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="st-panel p-3">
              <div className="st-data-label">FUEL MAP</div>
              <div className="font-mono text-base">{tune.fuel_map_ms.length}×{tune.fuel_map_ms[0].length}</div>
              <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">PULSE WIDTH (ms)</div>
            </div>
            <div className="st-panel p-3">
              <div className="st-data-label">IGNITION MAP</div>
              <div className="font-mono text-base">{tune.ignition_map_deg.length}×{tune.ignition_map_deg[0].length}</div>
              <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">DEG BTDC</div>
            </div>
            <div className="st-panel p-3">
              <div className="st-data-label">BOOST TARGET</div>
              <div className="font-mono text-base">{tune.boost_target_table ? `${tune.boost_target_table.length} cells` : "N/A"}</div>
              <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">{tune.boost_target_table ? "PEAK CAPPED" : "NA ENGINE"}</div>
            </div>
            <div className="st-panel p-3">
              <div className="st-data-label">PREDICTED HP</div>
              <div className="font-mono text-base">{fmt.hp(tune.predicted_hp.nominal)}</div>
              <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">
                {fmt.hp(tune.predicted_hp.low)} – {fmt.hp(tune.predicted_hp.high)}
              </div>
            </div>
          </div>

          {/* Warnings */}
          {tune.safety_envelope.warnings.length > 0 && (
            <div className="space-y-2">
              {tune.safety_envelope.warnings.map((w, i) => (
                <WarningBanner key={i} level={w.level} code={w.code} message={w.message} />
              ))}
            </div>
          )}

          {/* Fuel + Ignition maps */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Panel testId="fuel-map-panel">
              <PanelHeader
                label="FUEL MAP // INJECTOR PULSE WIDTH (ms)"
                sub="ROWS=MAP kPa · COLS=RPM"
                right={<ConfidenceBadge value={tune.confidence.fuel} label="FUEL" compact />}
              />
              <Heatmap
                matrix={tune.fuel_map_ms}
                rpmAxis={tune.axes.rpm}
                loadAxis={tune.axes.load_kpa}
                mode="fuel"
                unit="ms"
                decimals={2}
                testIdPrefix="cell-fuel"
              />
              <div className="mt-2 flex justify-end">
                <HeatmapLegend matrix={tune.fuel_map_ms} mode="fuel" unit="ms" label="SCALE" />
              </div>
            </Panel>

            <Panel testId="ignition-map-panel">
              <PanelHeader
                label="IGNITION MAP // DEG BTDC"
                sub="MBT-ANCHORED · KNOCK MARGIN"
                right={<ConfidenceBadge value={tune.confidence.ignition} label="IGN" compact />}
              />
              <Heatmap
                matrix={tune.ignition_map_deg}
                rpmAxis={tune.axes.rpm}
                loadAxis={tune.axes.load_kpa}
                mode="ignition"
                unit="°"
                decimals={1}
                testIdPrefix="cell-ign"
              />
              <div className="mt-2 flex justify-end">
                <HeatmapLegend matrix={tune.ignition_map_deg} mode="ignition" unit="°" label="SCALE" />
              </div>
            </Panel>
          </div>

          {/* Boost + AFR */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {boosted && tune.boost_target_table && (
              <Panel testId="boost-target-panel">
                <PanelHeader label="BOOST TARGET CURVE" sub="kPa @ RPM"
                             right={<ConfidenceBadge value={tune.confidence.boost} label="BOOST" compact />} />
                <div className="h-48 -mx-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={tune.boost_target_table} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                      <XAxis dataKey="rpm" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="#3f3f46" />
                      <YAxis tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="#3f3f46" />
                      <RTooltip
                        contentStyle={{ background: "#0e0e10", border: "1px solid #3f3f46", borderRadius: 0, fontFamily: "JetBrains Mono", fontSize: 11 }}
                        labelStyle={{ color: "#a1a1aa" }}
                        formatter={(v) => [`${v} kPa`, "TARGET"]}
                      />
                      <Line type="monotone" dataKey="boost_kpa" stroke="#F59E0B" strokeWidth={1.6} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-2">
                  PEAK CAPPED AT {fmt.kpa(tune.safety_envelope.boost_ceiling_kpa)} (envelope ceiling)
                </div>
              </Panel>
            )}

            <Panel testId="afr-target-panel" className={!boosted ? "xl:col-span-2" : ""}>
              <PanelHeader label="AFR TARGET TABLE" sub="LAMBDA × FUEL STOICH" />
              <Heatmap
                matrix={tune.afr_target_table}
                rpmAxis={tune.axes.rpm}
                loadAxis={tune.axes.load_kpa}
                mode="afr"
                unit=""
                decimals={2}
                testIdPrefix="cell-afr"
              />
            </Panel>
          </div>

          {/* Assumptions */}
          <Panel testId="assumptions-panel">
            <PanelHeader label="ASSUMPTIONS / HARDWARE NOTES" sub={tune.algorithm_version} />
            <ul className="font-mono text-[11px] text-[var(--st-text-secondary)] space-y-1 list-disc list-inside">
              {tune.assumptions.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </Panel>
        </>
      )}

      <div className="flex items-center justify-between gap-3 mt-2">
        <Button variant="ghost" onClick={onBack} data-testid="generate-back-btn"
                className="rounded-none font-mono text-xs uppercase tracking-widest text-[var(--st-text-muted)] hover:text-[var(--st-text)]">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to envelope
        </Button>
        <Button onClick={onNext} disabled={!tune} data-testid="generate-next-btn"
                className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs uppercase tracking-widest h-11 px-6">
          Review & Adjust <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}
