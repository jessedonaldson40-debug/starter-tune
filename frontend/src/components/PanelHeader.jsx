import React from "react";

export function PanelHeader({ index, label, sub, right, testId }) {
  return (
    <div className="flex items-center justify-between mb-3" data-testid={testId}>
      <div className="flex items-center gap-3">
        {index != null && (
          <span className="font-mono text-[10px] text-[var(--st-text-muted)] tracking-widest">
            {String(index).padStart(2, "0")}
          </span>
        )}
        <h3 className="st-panel-title">{label}</h3>
        {sub && (
          <span className="font-mono text-[10px] text-[var(--st-text-muted)] uppercase tracking-wider">
            {sub}
          </span>
        )}
      </div>
      {right}
    </div>
  );
}

export function Panel({ children, className = "", testId, raised = false }) {
  return (
    <section
      className={`${raised ? "st-panel-raised" : "st-panel"} p-4 ${className}`}
      data-testid={testId}
    >
      {children}
    </section>
  );
}
