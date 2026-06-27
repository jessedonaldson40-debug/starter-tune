import React from "react";
import { AlertTriangle, AlertOctagon, Info, ShieldCheck } from "lucide-react";

const ICONS = {
  danger: AlertOctagon,
  warning: AlertTriangle,
  info: Info,
  safe: ShieldCheck,
};

const STYLES = {
  danger: "border-l-[var(--st-danger)] bg-[#7F1D1D]/20 border-[#7F1D1D]/50 text-[var(--st-danger)]",
  warning: "border-l-[var(--st-warning)] bg-[#78350F]/20 border-[#78350F]/50 text-[var(--st-warning)]",
  info: "border-l-[var(--st-accent)] bg-[var(--st-accent-deep)]/15 border-[var(--st-accent-deep)]/50 text-[var(--st-accent)]",
  safe: "border-l-[var(--st-safe)] bg-[#064e3b]/25 border-[#064e3b]/50 text-[var(--st-safe)]",
};

export default function WarningBanner({ level = "warning", code, message, action, testId }) {
  const Icon = ICONS[level] || AlertTriangle;
  return (
    <div className={`flex items-start gap-3 border border-l-4 p-3 ${STYLES[level]}`} data-testid={testId || `warning-${code || level}`}>
      <Icon className="w-4 h-4 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        {code && (
          <div className="font-mono text-[10px] tracking-widest uppercase mb-0.5 opacity-80">
            {code}
          </div>
        )}
        <div className="text-sm text-[var(--st-text)]">{message}</div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
