import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProfile, compareGenerations } from "@/lib/api";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Heatmap, HeatmapLegend } from "@/components/Heatmap";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { fmt } from "@/lib/format";
import { ArrowLeft, GitCompareArrows } from "lucide-react";

export default function CompareView() {
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [a, setA] = useState(0);
  const [b, setB] = useState(0);
  const [diff, setDiff] = useState(null);

  useEffect(() => {
    getProfile(id).then((p) => {
      setProfile(p);
      const max = p.history.length - 1;
      setA(Math.max(0, max - 1));
      setB(max);
    });
  }, [id]);

  useEffect(() => {
    if (!profile) return;
    compareGenerations(id, a, b).then(setDiff);
  }, [profile, id, a, b]);

  const aTune = useMemo(() => profile && profile.history[a]?.tune_package, [profile, a]);
  const bTune = useMemo(() => profile && profile.history[b]?.tune_package, [profile, b]);

  if (!profile || !aTune || !bTune || !diff) {
    return <div className="text-center py-12 font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest">LOADING COMPARE VIEW…</div>;
  }

  const selectCls = "rounded-none bg-[var(--st-panel-deep)] border-[var(--st-border)] focus:ring-0 focus-visible:ring-0 h-9 font-mono text-xs";

  return (
    <div className="max-w-[1600px] mx-auto px-6 py-6" data-testid="compare-page">
      <div className="flex items-center justify-between mb-4">
        <Link to={`/profiles/${id}`} className="font-mono text-[10px] text-[var(--st-text-muted)] hover:text-[var(--st-accent)] uppercase tracking-widest flex items-center gap-2" data-testid="back-to-profile">
          <ArrowLeft className="w-3 h-3" /> Back to profile
        </Link>
        <div className="font-mono text-[10px] text-[var(--st-text-muted)] uppercase tracking-widest">
          FORENSIC COMPARE :: {profile.name}
        </div>
      </div>

      <Panel className="mb-4" testId="compare-controls">
        <div className="flex flex-wrap items-end gap-4">
          <GitCompareArrows className="w-5 h-5 text-[var(--st-accent)]" />
          <div>
            <div className="st-data-label mb-1">VERSION A (BASELINE)</div>
            <Select value={String(a)} onValueChange={(v) => setA(parseInt(v))}>
              <SelectTrigger className={`${selectCls} w-72`} data-testid="select-version-a"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                {profile.history.map((h, idx) => (
                  <SelectItem key={idx} value={String(idx)} className="rounded-none font-mono text-xs">
                    GEN #{idx + 1} — {h.note} — {fmt.date(h.created_at)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="text-[var(--st-text-muted)] font-mono">vs</div>
          <div>
            <div className="st-data-label mb-1">VERSION B (TARGET)</div>
            <Select value={String(b)} onValueChange={(v) => setB(parseInt(v))}>
              <SelectTrigger className={`${selectCls} w-72`} data-testid="select-version-b"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                {profile.history.map((h, idx) => (
                  <SelectItem key={idx} value={String(idx)} className="rounded-none font-mono text-xs">
                    GEN #{idx + 1} — {h.note} — {fmt.date(h.created_at)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="ml-auto flex gap-3">
            <div className="border border-[var(--st-border)] px-3 py-2 bg-[var(--st-panel-deep)]">
              <div className="st-data-label">Δ FUEL CELLS</div>
              <div className="font-mono text-base">{diff.fuel_diff.changed_count}</div>
            </div>
            <div className="border border-[var(--st-border)] px-3 py-2 bg-[var(--st-panel-deep)]">
              <div className="st-data-label">Δ IGN CELLS</div>
              <div className="font-mono text-base">{diff.ignition_diff.changed_count}</div>
            </div>
            <div className="border border-[var(--st-border)] px-3 py-2 bg-[var(--st-panel-deep)]">
              <div className="st-data-label">MAX Δ FUEL</div>
              <div className="font-mono text-base">{diff.fuel_diff.max_delta.toFixed(2)} ms</div>
            </div>
            <div className="border border-[var(--st-border)] px-3 py-2 bg-[var(--st-panel-deep)]">
              <div className="st-data-label">MAX Δ IGN</div>
              <div className="font-mono text-base">{diff.ignition_diff.max_delta.toFixed(1)}°</div>
            </div>
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Panel testId="compare-fuel-diff">
          <PanelHeader label="Δ FUEL MAP (B − A) // ms"
                       right={<HeatmapLegend matrix={diff.fuel_diff.deltas} mode="delta" unit="ms" />} />
          <Heatmap matrix={diff.fuel_diff.deltas} rpmAxis={aTune.axes.rpm} loadAxis={aTune.axes.load_kpa}
                   mode="delta" decimals={2} unit="ms" testIdPrefix="dcell-fuel" />
        </Panel>
        <Panel testId="compare-ign-diff">
          <PanelHeader label="Δ IGNITION MAP (B − A) // °"
                       right={<HeatmapLegend matrix={diff.ignition_diff.deltas} mode="delta" unit="°" />} />
          <Heatmap matrix={diff.ignition_diff.deltas} rpmAxis={aTune.axes.rpm} loadAxis={aTune.axes.load_kpa}
                   mode="delta" decimals={1} unit="°" testIdPrefix="dcell-ign" />
        </Panel>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
        <Panel testId="compare-side-a">
          <PanelHeader label={`A · GEN #${a + 1} · FUEL`} sub={fmt.date(profile.history[a].created_at)} />
          <Heatmap matrix={aTune.fuel_map_ms} rpmAxis={aTune.axes.rpm} loadAxis={aTune.axes.load_kpa}
                   mode="fuel" decimals={2} testIdPrefix="acell-fuel" />
        </Panel>
        <Panel testId="compare-side-b">
          <PanelHeader label={`B · GEN #${b + 1} · FUEL`} sub={fmt.date(profile.history[b].created_at)} />
          <Heatmap matrix={bTune.fuel_map_ms} rpmAxis={bTune.axes.rpm} loadAxis={bTune.axes.load_kpa}
                   mode="fuel" decimals={2} testIdPrefix="bcell-fuel" />
        </Panel>
      </div>
    </div>
  );
}
