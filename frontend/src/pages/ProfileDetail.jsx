import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getProfile, regenerateProfile, revertProfile } from "@/lib/api";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { Heatmap, HeatmapLegend } from "@/components/Heatmap";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import WarningBanner from "@/components/WarningBanner";
import ExportPanel from "@/components/ExportPanel";
import { fmt } from "@/lib/format";
import { ArrowLeft, Download, GitCompareArrows, History, RefreshCw, RotateCcw, Layers } from "lucide-react";
import { toast } from "sonner";
import { LineChart, Line, ResponsiveContainer, YAxis, XAxis, Tooltip as RTooltip } from "recharts";

export default function ProfileDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);

  const refresh = () => getProfile(id).then(setProfile);
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [id]);

  if (!profile) {
    return <div className="text-center py-12 font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest">LOADING PROFILE…</div>;
  }

  const active = profile.history[profile.active_generation_index];
  const tune = active.tune_package;
  const boosted = tune.boost_target_table != null;

  const onRegenerate = async () => {
    setBusy(true);
    try {
      await regenerateProfile(id, profile.engine_metadata, active.adjustments, "Re-run with current settings");
      await refresh();
      toast.success("New generation appended");
    } finally {
      setBusy(false);
    }
  };

  const onRevert = async (idx) => {
    if (idx === profile.active_generation_index) return;
    await revertProfile(id, idx);
    await refresh();
    toast.success(`Reverted to generation #${idx + 1}`);
  };

  return (
    <div className="max-w-[1600px] mx-auto px-6 py-6" data-testid="profile-detail-page">
      <div className="flex items-center justify-between mb-4">
        <Link to="/" className="font-mono text-[10px] text-[var(--st-text-muted)] hover:text-[var(--st-accent)] uppercase tracking-widest flex items-center gap-2" data-testid="back-to-dashboard">
          <ArrowLeft className="w-3 h-3" /> Back to overview
        </Link>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate(`/profiles/${id}/compare`)}
                  data-testid="open-compare-btn"
                  className="rounded-none border-[var(--st-border)] hover:border-[var(--st-accent)] hover:text-[var(--st-accent)] font-mono text-[11px] uppercase tracking-widest h-9">
            <GitCompareArrows className="w-3.5 h-3.5 mr-2" /> Compare / Forensic
          </Button>
          <Button variant="outline" onClick={onRegenerate} disabled={busy}
                  data-testid="regenerate-profile-btn"
                  className="rounded-none border-[var(--st-border)] hover:border-[var(--st-accent)] hover:text-[var(--st-accent)] font-mono text-[11px] uppercase tracking-widest h-9">
            <RefreshCw className={`w-3.5 h-3.5 mr-2 ${busy ? "animate-spin" : ""}`} /> Regenerate
          </Button>
          <Button onClick={() => setExportOpen(true)} data-testid="open-export-btn"
                  className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-[11px] uppercase tracking-widest h-9">
            <Download className="w-3.5 h-3.5 mr-2" /> Export / Handoff
          </Button>
        </div>
      </div>

      <Panel className="mb-4" testId="profile-header-panel">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] tracking-widest uppercase mb-2">
              PROFILE :: {profile.id.slice(0, 8)}
            </div>
            <h1 className="text-2xl font-medium tracking-tight text-[var(--st-text)]">{profile.name}</h1>
            <div className="font-mono text-xs text-[var(--st-text-secondary)] mt-2">
              {profile.engine_metadata.displacement_l}L · {profile.engine_metadata.cylinders}cyl ·{" "}
              {profile.engine_metadata.induction} · {profile.engine_metadata.fuel_type} ·{" "}
              TARGET {fmt.hp(profile.engine_metadata.target_hp)}
            </div>
            <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">
              CREATED {fmt.date(profile.created_at)} · UPDATED {fmt.date(profile.updated_at)} · ACTIVE GEN #{profile.active_generation_index + 1}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <ConfidenceBadge value={tune.confidence.overall} label="OVERALL" />
            <ConfidenceBadge value={tune.confidence.fuel} label="FUEL" />
            <ConfidenceBadge value={tune.confidence.ignition} label="IGN" />
            <ConfidenceBadge value={tune.confidence.safety} label="SAFETY" />
          </div>
        </div>
      </Panel>

      {tune.safety_envelope.warnings.length > 0 && (
        <div className="space-y-2 mb-4">
          {tune.safety_envelope.warnings.map((w, i) => (
            <WarningBanner key={i} level={w.level} code={w.code} message={w.message} />
          ))}
        </div>
      )}

      <Tabs defaultValue="maps" className="space-y-4" data-testid="profile-tabs">
        <TabsList className="rounded-none bg-[var(--st-panel)] border border-[var(--st-border)] p-0 h-10">
          <TabsTrigger value="maps" data-testid="tab-maps" className="rounded-none font-mono text-[11px] uppercase tracking-widest data-[state=active]:bg-[var(--st-panel-raised)] data-[state=active]:text-[var(--st-accent)] data-[state=active]:shadow-none h-10 px-5">
            <Layers className="w-3.5 h-3.5 mr-2" /> Tune Maps
          </TabsTrigger>
          <TabsTrigger value="tables" data-testid="tab-tables" className="rounded-none font-mono text-[11px] uppercase tracking-widest data-[state=active]:bg-[var(--st-panel-raised)] data-[state=active]:text-[var(--st-accent)] data-[state=active]:shadow-none h-10 px-5">
            Supporting Tables
          </TabsTrigger>
          <TabsTrigger value="envelope" data-testid="tab-envelope" className="rounded-none font-mono text-[11px] uppercase tracking-widest data-[state=active]:bg-[var(--st-panel-raised)] data-[state=active]:text-[var(--st-accent)] data-[state=active]:shadow-none h-10 px-5">
            Safety Envelope
          </TabsTrigger>
          <TabsTrigger value="history" data-testid="tab-history" className="rounded-none font-mono text-[11px] uppercase tracking-widest data-[state=active]:bg-[var(--st-panel-raised)] data-[state=active]:text-[var(--st-accent)] data-[state=active]:shadow-none h-10 px-5">
            <History className="w-3.5 h-3.5 mr-2" /> Generation History
          </TabsTrigger>
          <TabsTrigger value="exports" data-testid="tab-exports" className="rounded-none font-mono text-[11px] uppercase tracking-widest data-[state=active]:bg-[var(--st-panel-raised)] data-[state=active]:text-[var(--st-accent)] data-[state=active]:shadow-none h-10 px-5">
            Export Log
          </TabsTrigger>
        </TabsList>

        <TabsContent value="maps" className="space-y-4 mt-0">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Panel testId="detail-fuel-map">
              <PanelHeader label="FUEL MAP // PULSE WIDTH (ms)" sub="ROWS=MAP kPa · COLS=RPM"
                           right={<HeatmapLegend matrix={tune.fuel_map_ms} mode="fuel" unit="ms" />} />
              <Heatmap matrix={tune.fuel_map_ms} rpmAxis={tune.axes.rpm} loadAxis={tune.axes.load_kpa}
                       mode="fuel" decimals={2} unit="ms" testIdPrefix="pcell-fuel" />
            </Panel>
            <Panel testId="detail-ign-map">
              <PanelHeader label="IGNITION MAP // ° BTDC" sub="MBT MODEL"
                           right={<HeatmapLegend matrix={tune.ignition_map_deg} mode="ignition" unit="°" />} />
              <Heatmap matrix={tune.ignition_map_deg} rpmAxis={tune.axes.rpm} loadAxis={tune.axes.load_kpa}
                       mode="ignition" decimals={1} unit="°" testIdPrefix="pcell-ign" />
            </Panel>
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Panel testId="detail-afr-map">
              <PanelHeader label="AFR TARGET TABLE" sub="STOICH-BASED" />
              <Heatmap matrix={tune.afr_target_table} rpmAxis={tune.axes.rpm} loadAxis={tune.axes.load_kpa}
                       mode="afr" decimals={2} testIdPrefix="pcell-afr" />
            </Panel>
            {boosted && (
              <Panel testId="detail-boost">
                <PanelHeader label="BOOST TARGET CURVE" sub="kPa @ RPM · ENVELOPE-CAPPED" />
                <div className="h-64 -mx-2">
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
              </Panel>
            )}
          </div>
        </TabsContent>

        <TabsContent value="tables" className="space-y-4 mt-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Panel testId="detail-idle-table">
              <PanelHeader label="IDLE BASELINE TABLE" sub="VS COOLANT TEMP" />
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[var(--st-border)] text-[var(--st-text-secondary)]">
                      <th className="text-left py-2 px-2">CLT (°C)</th>
                      {tune.idle_table.clt_axis.map((c) => (
                        <th key={c} className="text-right py-2 px-2">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-[var(--st-border)]">
                      <td className="py-2 px-2 text-[var(--st-text-muted)]">TGT RPM</td>
                      {tune.idle_table.idle_target_rpm.map((v, i) => <td key={i} className="text-right py-2 px-2">{v}</td>)}
                    </tr>
                    <tr className="border-b border-[var(--st-border)]">
                      <td className="py-2 px-2 text-[var(--st-text-muted)]">BASE PW (ms)</td>
                      {tune.idle_table.idle_base_pw_ms.map((v, i) => <td key={i} className="text-right py-2 px-2">{v}</td>)}
                    </tr>
                    <tr>
                      <td className="py-2 px-2 text-[var(--st-text-muted)]">AFR TGT</td>
                      {tune.idle_table.idle_afr_target.map((v, i) => <td key={i} className="text-right py-2 px-2">{v}</td>)}
                    </tr>
                  </tbody>
                </table>
              </div>
            </Panel>
            <Panel testId="detail-coldstart-table">
              <PanelHeader label="COLD START TABLE" sub="ENRICHMENT % + DECAY" />
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr className="border-b border-[var(--st-border)] text-[var(--st-text-secondary)]">
                      <th className="text-left py-2 px-2">CLT (°C)</th>
                      {tune.cold_start_table.clt_axis.map((c) => (
                        <th key={c} className="text-right py-2 px-2">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-[var(--st-border)]">
                      <td className="py-2 px-2 text-[var(--st-text-muted)]">ENRICH %</td>
                      {tune.cold_start_table.enrichment_pct.map((v, i) => <td key={i} className="text-right py-2 px-2">{v}</td>)}
                    </tr>
                    <tr>
                      <td className="py-2 px-2 text-[var(--st-text-muted)]">DECAY (s)</td>
                      {tune.cold_start_table.decay_seconds.map((v, i) => <td key={i} className="text-right py-2 px-2">{v}</td>)}
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="text-[10px] font-mono text-[var(--st-text-muted)] mt-3">{tune.cold_start_table.notes}</div>
            </Panel>
          </div>
          <Panel testId="detail-ve-curve">
            <PanelHeader label="ESTIMATED VE CURVE" sub="USED FOR MASS AIRFLOW" />
            <div className="h-48 -mx-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={tune.ve_curve} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
                  <XAxis dataKey="rpm" tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="#3f3f46" />
                  <YAxis tick={{ fill: "#71717A", fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="#3f3f46" domain={[0.3, "auto"]} />
                  <RTooltip
                    contentStyle={{ background: "#0e0e10", border: "1px solid #3f3f46", borderRadius: 0, fontFamily: "JetBrains Mono", fontSize: 11 }}
                    formatter={(v) => [`${(v * 100).toFixed(1)}%`, "VE"]}
                  />
                  <Line type="monotone" dataKey="ve" stroke="#38BDF8" strokeWidth={1.6} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </TabsContent>

        <TabsContent value="envelope" className="space-y-4 mt-0">
          <Panel testId="detail-envelope">
            <PanelHeader label="SAFETY ENVELOPE" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                ["AFR FLOOR", tune.safety_envelope.afr_min],
                ["AFR CEILING", tune.safety_envelope.afr_max],
                ["IGN CEILING", fmt.deg(tune.safety_envelope.ignition_ceiling)],
                ["BOOST CEILING", tune.safety_envelope.boost_ceiling_kpa ? fmt.kpa(tune.safety_envelope.boost_ceiling_kpa) : "N/A"],
                ["INJ HEADROOM", fmt.pct(tune.safety_envelope.injector_headroom_pct)],
                ["TORQUE BASE", `${tune.safety_envelope.torque_baseline_nm} Nm`],
                ["KNOCK SENS.", tune.safety_envelope.knock_sensitivity.toUpperCase()],
                ["THERMAL RISK", tune.safety_envelope.thermal_risk.toUpperCase()],
              ].map(([k, v]) => (
                <div key={k} className="border border-[var(--st-border)] bg-[var(--st-panel-deep)] p-3">
                  <div className="st-data-label">{k}</div>
                  <div className="font-mono text-base mt-1">{v}</div>
                </div>
              ))}
            </div>
          </Panel>
          <Panel testId="detail-assumptions">
            <PanelHeader label="GENERATION ASSUMPTIONS" sub={tune.algorithm_version} />
            <ul className="font-mono text-[11px] text-[var(--st-text-secondary)] space-y-1 list-disc list-inside">
              {tune.assumptions.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </Panel>
        </TabsContent>

        <TabsContent value="history" className="space-y-4 mt-0">
          <Panel testId="detail-history-panel">
            <PanelHeader label="GENERATION HISTORY" sub={`${profile.history.length} VERSIONS`} />
            <div className="space-y-2">
              {profile.history.map((h, idx) => (
                <div key={idx} className={[
                  "border p-3 flex items-center justify-between gap-3",
                  idx === profile.active_generation_index
                    ? "border-[var(--st-accent)] bg-[var(--st-accent-deep)]/15"
                    : "border-[var(--st-border)]"
                ].join(" ")} data-testid={`history-${idx}`}>
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-[11px] uppercase tracking-widest text-[var(--st-text)]">
                      GEN #{idx + 1} · {fmt.date(h.created_at)}
                      {idx === profile.active_generation_index && (
                        <span className="ml-2 text-[var(--st-accent)]">ACTIVE</span>
                      )}
                    </div>
                    <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">{h.note}</div>
                    <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">
                      AFR {h.adjustments.afr_bias?.toFixed(2)} ·
                      TIM {h.adjustments.timing_bias?.toFixed(2)} ·
                      BST {h.adjustments.boost_intent?.toFixed(2)} ·
                      DRIVE {h.adjustments.drivability_bias?.toFixed(2)}
                      {h.diff_vs_previous && (
                        <> · Δ FUEL {h.diff_vs_previous.fuel.changed_count} cells · Δ IGN {h.diff_vs_previous.ignition.changed_count} cells</>
                      )}
                    </div>
                  </div>
                  {idx !== profile.active_generation_index && (
                    <Button variant="outline" size="sm"
                            onClick={() => onRevert(idx)}
                            data-testid={`revert-${idx}`}
                            className="rounded-none border-[var(--st-border)] hover:border-[var(--st-accent)] hover:text-[var(--st-accent)] font-mono text-[10px] uppercase tracking-widest">
                      <RotateCcw className="w-3 h-3 mr-2" /> Make Active
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </Panel>
        </TabsContent>

        <TabsContent value="exports" className="space-y-4 mt-0">
          <Panel testId="detail-exports-panel">
            <PanelHeader label="EXPORT / HANDOFF LOG" sub={`${(profile.exports || []).length} ARTIFACTS`} />
            {(!profile.exports || profile.exports.length === 0) ? (
              <div className="font-mono text-xs text-[var(--st-text-muted)] py-6 text-center uppercase tracking-widest">
                [ idle ] no handoffs yet · click EXPORT / HANDOFF to start
              </div>
            ) : (
              <pre className="font-mono text-[11px] leading-relaxed text-[var(--st-text-secondary)] max-h-72 overflow-auto whitespace-pre-wrap bg-[var(--st-panel-deep)] p-3 border border-[var(--st-border)]">
                {profile.exports.map((e) => e.log_line).join("\n")}
              </pre>
            )}
          </Panel>
        </TabsContent>
      </Tabs>

      <ExportPanel open={exportOpen} onOpenChange={setExportOpen} profileId={profile.id} profileName={profile.name} />
    </div>
  );
}
