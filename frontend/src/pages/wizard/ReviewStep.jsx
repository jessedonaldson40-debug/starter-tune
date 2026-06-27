import React, { useEffect, useMemo, useState } from "react";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Heatmap, HeatmapLegend } from "@/components/Heatmap";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import WarningBanner from "@/components/WarningBanner";
import KnockPullEditor from "@/components/KnockPullEditor";
import { generateTune } from "@/lib/api";
import { fmt } from "@/lib/format";
import { ArrowLeft, ArrowRight, History, RotateCcw } from "lucide-react";

function AdjustSlider({ label, value, onChange, min = -1, max = 1, step = 0.05, leftLabel, rightLabel, testId }) {
  return (
    <div className="space-y-2" data-testid={testId}>
      <div className="flex items-center justify-between">
        <span className="st-data-label">{label}</span>
        <span className="font-mono text-xs tabular-nums text-[var(--st-accent)]">
          {value > 0 ? "+" : ""}{value.toFixed(2)}
        </span>
      </div>
      <Slider
        min={min} max={max} step={step}
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        className="py-2"
      />
      <div className="flex items-center justify-between font-mono text-[9px] text-[var(--st-text-muted)] uppercase tracking-widest">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
    </div>
  );
}

function buildChangedMask(prev, curr, threshold = 0.05) {
  if (!prev || !curr) return null;
  return curr.map((row, r) => row.map((v, c) => Math.abs(v - prev[r][c]) > threshold));
}

export default function ReviewStep({
  intake, tune, setTune, adjustments, setAdjustments,
  history, setHistory, onBack, onNext,
}) {
  const [busy, setBusy] = useState(false);
  const [showDiff, setShowDiff] = useState(true);
  const [prevTune, setPrevTune] = useState(history[0]?.tune || tune);

  // Regenerate after adjustments
  const apply = async (next) => {
    setBusy(true);
    try {
      const res = await generateTune(intake, next);
      setPrevTune(tune);
      setTune(res);
      setHistory((h) => [{ tune: res, adjustments: next, ts: new Date().toISOString(), note: "Adjusted" }, ...h]);
    } finally {
      setBusy(false);
    }
  };

  const onAdj = (key, value) => {
    const next = { ...adjustments, [key]: value };
    setAdjustments(next);
  };

  // Debounce apply
  useEffect(() => {
    const t = setTimeout(() => apply(adjustments), 280);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adjustments.afr_bias, adjustments.timing_bias, adjustments.boost_intent, adjustments.drivability_bias, JSON.stringify(adjustments.knock_pull_zones)]);

  const fuelMask = useMemo(() => prevTune ? buildChangedMask(prevTune.fuel_map_ms, tune?.fuel_map_ms, 0.03) : null, [prevTune, tune]);
  const ignMask  = useMemo(() => prevTune ? buildChangedMask(prevTune.ignition_map_deg, tune?.ignition_map_deg, 0.2) : null, [prevTune, tune]);

  // Build deltas if showDiff
  const fuelDeltas = useMemo(() => {
    if (!prevTune || !tune) return null;
    return tune.fuel_map_ms.map((row, r) => row.map((v, c) => +(v - prevTune.fuel_map_ms[r][c]).toFixed(3)));
  }, [prevTune, tune]);
  const ignDeltas = useMemo(() => {
    if (!prevTune || !tune) return null;
    return tune.ignition_map_deg.map((row, r) => row.map((v, c) => +(v - prevTune.ignition_map_deg[r][c]).toFixed(2)));
  }, [prevTune, tune]);

  const revert = (idx) => {
    const target = history[idx];
    if (!target) return;
    setPrevTune(tune);
    setTune(target.tune);
    setAdjustments(target.adjustments);
    setHistory((h) => [{ ...target, ts: new Date().toISOString(), note: `Reverted to v${h.length - idx}` }, ...h]);
  };

  if (!tune) {
    return (
      <div className="text-center py-12 font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest">
        NO TUNE LOADED — RETURN TO STEP 3
      </div>
    );
  }

  const boosted = intake.induction !== "NA";
  const changeSummary = (() => {
    if (!fuelMask || !ignMask) return null;
    const f = fuelMask.flat().filter(Boolean).length;
    const i = ignMask.flat().filter(Boolean).length;
    return { f, i };
  })();

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4" data-testid="review-step">
      {/* Left: adjust controls + history */}
      <div className="lg:col-span-1 flex flex-col gap-4">
        <Panel testId="adjust-panel">
          <PanelHeader index={4} label="STEP 04 // ADJUST" sub={busy ? "REGENERATING…" : "LIVE BIAS"} />
          <div className="space-y-5">
            <AdjustSlider label="AFR BIAS"
                          value={adjustments.afr_bias} onChange={(v) => onAdj("afr_bias", v)}
                          leftLabel="RICHER" rightLabel="LEANER" testId="slider-afr-bias" />
            <AdjustSlider label="TIMING AGGRESSIVENESS"
                          value={adjustments.timing_bias} onChange={(v) => onAdj("timing_bias", v)}
                          leftLabel="CONSERVATIVE" rightLabel="AGGRESSIVE" testId="slider-timing-bias" />
            {boosted && (
              <AdjustSlider label="BOOST INTENT"
                            value={adjustments.boost_intent} onChange={(v) => onAdj("boost_intent", v)}
                            leftLabel="LOW (SAFE)" rightLabel="TO CEILING" testId="slider-boost-intent" />
            )}
            <AdjustSlider label="DRIVABILITY ↔ PERFORMANCE"
                          value={adjustments.drivability_bias} onChange={(v) => onAdj("drivability_bias", v)}
                          leftLabel="STREET" rightLabel="TRACK" testId="slider-drivability" />
          </div>

          <div className="mt-6 pt-4 border-t border-[var(--st-border)] flex items-center justify-between">
            <span className="st-data-label">SHOW DIFF OVERLAY</span>
            <Switch checked={showDiff} onCheckedChange={setShowDiff} data-testid="toggle-diff" />
          </div>
        </Panel>

        <Panel testId="history-panel">
          <PanelHeader label="UNDO STACK" sub={`${history.length} VERSIONS`} right={<History className="w-4 h-4 text-[var(--st-text-muted)]" />} />
          <div className="space-y-1 max-h-72 overflow-auto">
            {history.map((h, i) => (
              <button key={i}
                      onClick={() => i > 0 && revert(i)}
                      disabled={i === 0}
                      data-testid={`history-entry-${i}`}
                      className={[
                        "w-full text-left border p-2 transition-colors",
                        i === 0 ? "border-[var(--st-accent)] bg-[var(--st-accent-deep)]/15 cursor-default"
                                : "border-[var(--st-border)] hover:border-[var(--st-border-strong)] cursor-pointer"
                      ].join(" ")}>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-text)]">
                    v{history.length - i} {i === 0 ? "· ACTIVE" : ""}
                  </span>
                  {i > 0 && <RotateCcw className="w-3 h-3 text-[var(--st-text-muted)]" />}
                </div>
                <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">{h.note}</div>
                <div className="font-mono text-[9px] text-[var(--st-text-muted)] mt-1 truncate">
                  AFR {h.adjustments.afr_bias.toFixed(2)} · TIM {h.adjustments.timing_bias.toFixed(2)}
                  {boosted ? ` · BST ${h.adjustments.boost_intent.toFixed(2)}` : ""}
                </div>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      {/* Right: live maps */}
      <div className="lg:col-span-3 flex flex-col gap-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="review-confidence">
          <div className="st-panel p-3">
            <ConfidenceBadge value={tune.confidence.overall} label="OVERALL" testId="conf-overall" />
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-2">TUNE PACKAGE</div>
          </div>
          <div className="st-panel p-3">
            <ConfidenceBadge value={tune.confidence.fuel} label="FUEL" testId="conf-fuel" />
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-2">VE × AFR × INJ</div>
          </div>
          <div className="st-panel p-3">
            <ConfidenceBadge value={tune.confidence.ignition} label="IGN" testId="conf-ign" />
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-2">MBT MODEL</div>
          </div>
          <div className="st-panel p-3">
            <ConfidenceBadge value={tune.confidence.safety} label="SAFETY" testId="conf-safety" />
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-2">ENVELOPE</div>
          </div>
        </div>

        {changeSummary && (changeSummary.f > 0 || changeSummary.i > 0) && (
          <WarningBanner
            level="info"
            code="CHANGED_CELLS"
            message={`Adjustment shifted ${changeSummary.f} fuel cells and ${changeSummary.i} ignition cells vs previous generation.`}
            testId="changed-cells-banner"
          />
        )}

        {/* Fuel map */}
        <Panel testId="review-fuel-map">
          <PanelHeader label={showDiff ? "FUEL MAP // ΔPULSE WIDTH (ms)" : "FUEL MAP // PULSE WIDTH (ms)"}
                       sub="ROWS=MAP kPa · COLS=RPM"
                       right={<HeatmapLegend matrix={showDiff && fuelDeltas ? fuelDeltas : tune.fuel_map_ms}
                                             mode={showDiff ? "delta" : "fuel"} unit="ms" />} />
          <Heatmap
            matrix={showDiff && fuelDeltas ? fuelDeltas : tune.fuel_map_ms}
            rpmAxis={tune.axes.rpm}
            loadAxis={tune.axes.load_kpa}
            mode={showDiff ? "delta" : "fuel"}
            decimals={showDiff ? 2 : 2}
            unit="ms"
            changedMask={fuelMask}
            testIdPrefix="rcell-fuel"
          />
        </Panel>

        {/* Ignition map */}
        <Panel testId="review-ign-map">
          <PanelHeader label={showDiff ? "IGNITION MAP // Δ° BTDC" : "IGNITION MAP // ° BTDC"}
                       sub="MBT MODEL · KNOCK MARGIN"
                       right={<HeatmapLegend matrix={showDiff && ignDeltas ? ignDeltas : tune.ignition_map_deg}
                                             mode={showDiff ? "delta" : "ignition"} unit="°" />} />
          <Heatmap
            matrix={showDiff && ignDeltas ? ignDeltas : tune.ignition_map_deg}
            rpmAxis={tune.axes.rpm}
            loadAxis={tune.axes.load_kpa}
            mode={showDiff ? "delta" : "ignition"}
            decimals={1}
            unit="°"
            changedMask={ignMask}
            testIdPrefix="rcell-ign"
          />
        </Panel>

        {/* Why did this change panel */}
        <Panel testId="why-changed-panel">
          <PanelHeader label="WHY DID THIS CHANGE?" sub="ADJUSTMENT RATIONALE" />
          <ul className="space-y-2 text-xs text-[var(--st-text-secondary)] leading-relaxed">
            {adjustments.afr_bias < -0.1 && <li>• AFR shifted richer in high-load cells for charge cooling and knock margin.</li>}
            {adjustments.afr_bias > 0.1 && <li>• AFR shifted leaner in cruise cells for economy; bounded by stoich ceiling.</li>}
            {adjustments.timing_bias < -0.1 && <li>• Ignition pulled across the map for conservative knock margin.</li>}
            {adjustments.timing_bias > 0.1 && <li>• Ignition advanced toward MBT, still clamped by envelope ceiling.</li>}
            {adjustments.boost_intent < -0.1 && boosted && <li>• Boost target lowered for spool safety and lower thermal load.</li>}
            {adjustments.boost_intent > 0.1 && boosted && <li>• Boost target raised toward envelope ceiling; cannot exceed {fmt.kpa(tune.safety_envelope.boost_ceiling_kpa)}.</li>}
            {Math.abs(adjustments.drivability_bias) > 0.1 && <li>• VE estimate shifted to reflect {adjustments.drivability_bias > 0 ? "performance" : "drivability"} cam profile assumption.</li>}
            {tune.adjustments_applied?.knock_pull_applied && <li>• Manual knock-pull applied via Knock Pull Editor — specific RPM/load zones now have reduced timing for additional knock margin.</li>}
            {Math.abs(adjustments.afr_bias) < 0.1 && Math.abs(adjustments.timing_bias) < 0.1
              && Math.abs(adjustments.boost_intent) < 0.1 && Math.abs(adjustments.drivability_bias) < 0.1
              && !tune.adjustments_applied?.knock_pull_applied &&
              <li className="text-[var(--st-text-muted)]">No adjustments applied. Baseline conservative starter tune.</li>}
          </ul>
        </Panel>

        {/* Knock Pull Editor */}
        <KnockPullEditor
          value={adjustments.knock_pull_zones}
          onChange={(zones) => setAdjustments({ ...adjustments, knock_pull_zones: zones })}
          rpmAxis={tune.axes.rpm}
          loadAxis={tune.axes.load_kpa}
        />

        <div className="flex items-center justify-between gap-3 mt-2">
          <Button variant="ghost" onClick={onBack} data-testid="review-back-btn"
                  className="rounded-none font-mono text-xs uppercase tracking-widest text-[var(--st-text-muted)] hover:text-[var(--st-text)]">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to generation
          </Button>
          <Button onClick={onNext} data-testid="review-next-btn"
                  className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs uppercase tracking-widest h-11 px-6">
            Save as Profile <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    </div>
  );
}
