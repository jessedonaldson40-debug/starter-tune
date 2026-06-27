import React from "react";

const STEPS = [
  { idx: 1, label: "INTAKE", desc: "Engine spec" },
  { idx: 2, label: "ENVELOPE", desc: "Safety bounds" },
  { idx: 3, label: "GENERATE", desc: "Base maps" },
  { idx: 4, label: "REVIEW", desc: "Adjust & verify" },
  { idx: 5, label: "SAVE", desc: "Create profile" },
];

export default function WizardStepper({ current, onJump }) {
  return (
    <div className="border-y border-[var(--st-border)] bg-[var(--st-panel)]" data-testid="wizard-stepper">
      <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center gap-2 overflow-x-auto">
        {STEPS.map((s, i) => {
          const active = s.idx === current;
          const done = s.idx < current;
          const clickable = done && onJump;
          return (
            <React.Fragment key={s.idx}>
              <button
                type="button"
                disabled={!clickable}
                onClick={() => clickable && onJump(s.idx)}
                data-testid={`stepper-step-${s.idx}`}
                className={[
                  "flex items-center gap-2 py-3 px-2 transition-colors font-mono text-[11px] tracking-widest uppercase border-b-2",
                  active ? "border-[var(--st-accent)] text-[var(--st-accent)]"
                         : done ? "border-[var(--st-safe)] text-[var(--st-safe)] hover:text-[var(--st-text)]"
                                : "border-transparent text-[var(--st-text-muted)]",
                ].join(" ")}
              >
                <span className={[
                  "w-6 h-6 flex items-center justify-center border text-[10px]",
                  active ? "border-[var(--st-accent)] bg-[var(--st-accent-deep)]/30"
                         : done ? "border-[var(--st-safe)] bg-[var(--st-safe)]/15"
                                : "border-[var(--st-border)]",
                ].join(" ")}>
                  {done ? "✓" : s.idx}
                </span>
                <span className="flex flex-col items-start leading-none">
                  <span>{s.label}</span>
                  <span className="text-[9px] text-[var(--st-text-muted)] normal-case tracking-wider mt-1">{s.desc}</span>
                </span>
              </button>
              {i < STEPS.length - 1 && (
                <span className="text-[var(--st-text-muted)] text-xs font-mono">―</span>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
