import React from "react";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { fmt } from "@/lib/format";
import { Flame, RotateCcw, Wand2 } from "lucide-react";

/**
 * KnockPullEditor — 4x4 zone grid of additive ignition pull values (negative degrees).
 * Rows = RPM quartile (low→high). Cols = Load quartile (low→high).
 *
 * Layout convention matches the heatmap: high load on top row of the table,
 * low RPM on the left column.
 */

const ZONE_RPM_LABELS = ["LOW", "MID-LO", "MID-HI", "HIGH"];
const ZONE_LOAD_LABELS = ["LIGHT", "CRUISE", "HIGH", "PEAK"];

export default function KnockPullEditor({ value, onChange, rpmAxis, loadAxis, testId = "knock-pull-editor" }) {
  const zones = value || Array.from({ length: 4 }, () => [0, 0, 0, 0]);

  const updateCell = (zr, zl, raw) => {
    const num = raw === "" || raw === "-" ? 0 : parseFloat(raw);
    if (Number.isNaN(num)) return;
    const next = zones.map((r) => r.slice());
    next[zr][zl] = Math.max(-15, Math.min(0, num)); // clamp 0..-15
    onChange(next);
  };

  const clearAll = () => onChange(Array.from({ length: 4 }, () => [0, 0, 0, 0]));

  const applyPreset = (preset) => {
    let next = Array.from({ length: 4 }, () => [0, 0, 0, 0]);
    if (preset === "high_load") {
      // pull on the high-load columns
      for (let zr = 0; zr < 4; zr++) {
        next[zr][2] = -1.0;
        next[zr][3] = -2.5;
      }
    } else if (preset === "top_end_boost") {
      // top RPM + top load
      next[3][2] = -1.5;
      next[3][3] = -3.0;
      next[2][3] = -1.5;
    } else if (preset === "midrange") {
      // mid RPM + high load — common knock zone
      next[1][2] = -1.0;
      next[1][3] = -2.0;
      next[2][2] = -1.0;
      next[2][3] = -2.0;
    }
    onChange(next);
  };

  // RPM/load ranges shown to user — derived from actual axes
  const rpmRanges = (() => {
    if (!rpmAxis) return ZONE_RPM_LABELS.map((l) => l);
    return [0, 1, 2, 3].map((i) => {
      const lo = rpmAxis[i * 4];
      const hi = rpmAxis[Math.min(rpmAxis.length - 1, i * 4 + 3)];
      return `${lo}–${hi}`;
    });
  })();
  const loadRanges = (() => {
    if (!loadAxis) return ZONE_LOAD_LABELS.map((l) => l);
    return [0, 1, 2, 3].map((i) => {
      const lo = loadAxis[i * 4];
      const hi = loadAxis[Math.min(loadAxis.length - 1, i * 4 + 3)];
      return `${lo}–${hi}`;
    });
  })();

  const totalCells = zones.flat().filter((v) => v < 0).length;
  const maxPull = zones.flat().reduce((m, v) => Math.min(m, v), 0);

  return (
    <Panel testId={testId}>
      <PanelHeader
        label="KNOCK PULL EDITOR"
        sub="4×4 ZONES · OVERLAYS IGN MAP"
        right={
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-[var(--st-text-muted)] uppercase tracking-widest">
              {totalCells > 0 ? `${totalCells} ZONES PULLED · MAX ${maxPull.toFixed(1)}°` : "NO PULL APPLIED"}
            </span>
            <button
              type="button"
              onClick={clearAll}
              disabled={totalCells === 0}
              data-testid="knock-pull-clear"
              className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-text-muted)] hover:text-[var(--st-danger)] disabled:opacity-30 disabled:cursor-not-allowed border border-[var(--st-border)] px-2 py-1 flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" /> Clear
            </button>
          </div>
        }
      />

      {/* Presets */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="st-data-label flex items-center gap-1">
          <Wand2 className="w-3 h-3" /> PRESETS
        </span>
        {[
          { key: "high_load", label: "High-load pull (−1 / −2.5°)" },
          { key: "midrange", label: "Midrange detonation (−1 / −2°)" },
          { key: "top_end_boost", label: "Top-end boost (−1.5 / −3°)" },
        ].map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => applyPreset(p.key)}
            data-testid={`knock-preset-${p.key}`}
            className="border border-[var(--st-border)] hover:border-[var(--st-warning)] hover:text-[var(--st-warning)] px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-[var(--st-text-secondary)]"
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse" style={{ tableLayout: "fixed" }}>
          <thead>
            <tr>
              <th className="bg-[var(--st-panel-raised)] border border-[var(--st-border)] px-2 py-1 st-data-label text-left">
                LOAD ↓ / RPM →
              </th>
              {rpmRanges.map((label, i) => (
                <th key={i} className="bg-[var(--st-panel-raised)] border border-[var(--st-border)] px-2 py-1 st-data-label text-center">
                  {label}<br/>
                  <span className="text-[9px] text-[var(--st-text-muted)] font-normal normal-case tracking-wider">
                    {ZONE_RPM_LABELS[i]}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[3, 2, 1, 0].map((zl) => (
              <tr key={zl}>
                <th className="bg-[var(--st-panel-raised)] border border-[var(--st-border)] px-2 py-1 st-data-label text-left">
                  {loadRanges[zl]}<br/>
                  <span className="text-[9px] text-[var(--st-text-muted)] font-normal normal-case tracking-wider">
                    {ZONE_LOAD_LABELS[zl]}
                  </span>
                </th>
                {[0, 1, 2, 3].map((zr) => {
                  const v = zones[zr][zl];
                  const active = v < 0;
                  return (
                    <td
                      key={zr}
                      className="border border-[var(--st-border)] p-0"
                      style={{
                        background: active ? "rgba(239,68,68,0.16)" : "var(--st-panel-deep)",
                      }}
                    >
                      <label className="flex items-center justify-center gap-1 p-2 cursor-text">
                        {active && <Flame className="w-3 h-3 text-[var(--st-danger)]" />}
                        <input
                          type="number"
                          step="0.5"
                          min="-15"
                          max="0"
                          value={v === 0 ? "" : v}
                          placeholder="0.0"
                          onChange={(e) => updateCell(zr, zl, e.target.value)}
                          data-testid={`knock-cell-${zr}-${zl}`}
                          className="bg-transparent w-14 text-center font-mono text-sm tabular-nums focus:outline-none"
                          style={{
                            color: active ? "var(--st-danger)" : "var(--st-text-secondary)",
                          }}
                        />
                        <span className="font-mono text-[10px] text-[var(--st-text-muted)]">°</span>
                      </label>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-3 leading-relaxed">
        Negative values subtract from the envelope-clamped ignition map. Each zone covers 4 RPM × 4 load cells of the 16×16 map.
        Pull is floored at 0° — the system will never produce negative timing.
      </div>
    </Panel>
  );
}
