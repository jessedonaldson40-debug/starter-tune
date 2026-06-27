import React from "react";
import { colorFuel, colorIgnition, colorDelta, textOn, matMinMax, matAbsMax } from "@/lib/heatmap";

/**
 * Industrial heatmap table.
 * mode: 'fuel' | 'ignition' | 'delta' | 'afr'
 */
export function Heatmap({
  matrix,
  rpmAxis,
  loadAxis,
  mode = "fuel",
  unit = "",
  changedMask = null,    // 2D boolean of same shape, highlights border
  decimals = 2,
  testIdPrefix = "cell",
  className = "",
}) {
  const isDelta = mode === "delta";
  const [mn, mx] = isDelta ? [0, 0] : matMinMax(matrix);
  const absMax = isDelta ? matAbsMax(matrix) : 0;

  const colorFor = (v) => {
    if (mode === "fuel" || mode === "afr") return colorFuel(v, mn, mx);
    if (mode === "ignition") return colorIgnition(v, mn, mx);
    if (mode === "delta") return colorDelta(v, absMax);
    return "#222";
  };

  if (!matrix || !matrix.length) {
    return (
      <div className="p-8 text-center text-[var(--st-text-muted)] font-mono text-xs uppercase border border-[var(--st-border)]">
        NO MAP DATA
      </div>
    );
  }

  return (
    <div className={`overflow-x-auto border border-[var(--st-border)] bg-[var(--st-panel-deep)] ${className}`} data-testid={`heatmap-${mode}`}>
      <table className="border-collapse w-full" style={{ tableLayout: "fixed" }}>
        <thead>
          <tr>
            <th className="bg-[var(--st-panel-raised)] text-[10px] font-mono text-[var(--st-text-secondary)] sticky left-0 z-10 px-2 py-1 border-r border-b border-[var(--st-border)] text-left whitespace-nowrap">
              MAP\RPM
            </th>
            {rpmAxis.map((r) => (
              <th key={r}
                  className="bg-[var(--st-panel-raised)] text-[10px] font-mono text-[var(--st-text-secondary)] px-1 py-1 border-b border-r border-[var(--st-border)] font-bold text-center">
                {r}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* Render in reverse: highest load at top, low load at bottom (standard tuning convention) */}
          {[...Array(loadAxis.length).keys()].reverse().map((lIdx) => (
            <tr key={lIdx}>
              <th className="bg-[var(--st-panel-raised)] text-[10px] font-mono text-[var(--st-text-secondary)] sticky left-0 z-10 px-2 py-1 border-r border-b border-[var(--st-border)] text-left whitespace-nowrap">
                {loadAxis[lIdx]}
              </th>
              {rpmAxis.map((_, rIdx) => {
                const v = matrix[rIdx][lIdx];
                const bg = colorFor(v);
                const fg = textOn(bg);
                const changed = changedMask && changedMask[rIdx] && changedMask[rIdx][lIdx];
                return (
                  <td key={rIdx}
                      data-testid={`${testIdPrefix}-${rpmAxis[rIdx]}-${loadAxis[lIdx]}`}
                      className="text-center font-mono text-[11px] select-none transition-colors"
                      style={{
                        background: bg,
                        color: fg,
                        borderRight: "1px solid rgba(0,0,0,0.18)",
                        borderBottom: "1px solid rgba(0,0,0,0.18)",
                        boxShadow: changed ? "inset 0 0 0 1px #38bdf8" : "none",
                        padding: "4px 2px",
                        minWidth: 38,
                      }}
                      title={`RPM ${rpmAxis[rIdx]} • MAP ${loadAxis[lIdx]} kPa\n${v}${unit ? " " + unit : ""}`}>
                    {isDelta && v > 0 ? "+" : ""}{Number(v).toFixed(decimals)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Compact legend bar for a heatmap. */
export function HeatmapLegend({ matrix, mode = "fuel", unit = "", label = "" }) {
  const isDelta = mode === "delta";
  const [mn, mx] = isDelta ? [-matAbsMax(matrix), matAbsMax(matrix)] : matMinMax(matrix);
  const samples = [0, 0.25, 0.5, 0.75, 1].map((t) => mn + (mx - mn) * t);

  const colorFor = (v) => {
    if (mode === "fuel" || mode === "afr") return colorFuel(v, mn, mx);
    if (mode === "ignition") return colorIgnition(v, mn, mx);
    if (mode === "delta") return colorDelta(v, Math.max(Math.abs(mn), Math.abs(mx)));
    return "#333";
  };

  return (
    <div className="flex items-center gap-3 font-mono text-[10px] text-[var(--st-text-secondary)]">
      {label && <span className="uppercase tracking-wider">{label}</span>}
      <div className="flex items-stretch h-3 border border-[var(--st-border)]">
        {samples.map((v, i) => (
          <div key={i} className="w-8" style={{ background: colorFor(v) }} />
        ))}
      </div>
      <span className="tabular-nums">{Number(mn).toFixed(2)} {unit}</span>
      <span>→</span>
      <span className="tabular-nums">{Number(mx).toFixed(2)} {unit}</span>
    </div>
  );
}
