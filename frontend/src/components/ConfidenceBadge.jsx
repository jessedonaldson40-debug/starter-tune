import React from "react";
import { confidenceLabel, confidenceTone } from "@/lib/format";

const TONE = {
  safe: { color: "#10B981", bg: "#064e3b", label: "SAFE" },
  warning: { color: "#F59E0B", bg: "#78350F", label: "WARN" },
  danger: { color: "#EF4444", bg: "#7F1D1D", label: "RISK" },
};

export default function ConfidenceBadge({ value, label, compact = false, testId }) {
  const tone = TONE[confidenceTone(value)];
  return (
    <div
      className={[
        "inline-flex items-center gap-2 border px-2 py-1 font-mono text-[10px] tracking-widest uppercase",
      ].join(" ")}
      style={{ borderColor: tone.color, color: tone.color, background: `${tone.bg}33` }}
      data-testid={testId || "confidence-badge"}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: tone.color }} />
      {label && <span className="opacity-80">{label}</span>}
      <span className="tabular-nums">{Math.round(value * 100)}%</span>
      {!compact && <span className="opacity-70">{confidenceLabel(value)}</span>}
    </div>
  );
}
