import React, { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Activity, FileSearch, ScanLine, FileCog } from "lucide-react";
import { exportProfile, listExportTargets } from "@/lib/api";
import { toast } from "sonner";
import { fmt } from "@/lib/format";

const ICONS = {
  diagsim: Activity,
  inspector: FileSearch,
  forensic: ScanLine,
  ecu: FileCog,
};

export default function ExportPanel({ open, onOpenChange, profileId, profileName }) {
  const [targets, setTargets] = useState({});
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(null);
  const [artifact, setArtifact] = useState(null);

  useEffect(() => {
    if (!open) return;
    listExportTargets().then(setTargets).catch(() => {});
  }, [open]);

  const handleExport = async (key) => {
    setBusy(key);
    try {
      const res = await exportProfile(profileId, key);
      setArtifact(res);
      setLog((prev) => [
        `[${fmt.date(res.generated_at)}] HANDOFF :: ${res.target_name}`,
        `  artifact_id     ${res.artifact_id}`,
        `  format          ${res.format}`,
        `  fuel_cells      ${res.tune_summary.fuel_cells}`,
        `  ignition_cells  ${res.tune_summary.ignition_cells}`,
        `  confidence      ${(res.tune_summary.confidence_overall * 100).toFixed(0)}%`,
        `  warnings        ${res.tune_summary.warnings_count}`,
        `  source_gen_idx  ${res.source_generation_index}`,
        "",
        ...prev,
      ]);
      toast.success(`${res.target_name} handoff complete`, {
        description: `Artifact ${res.artifact_id.slice(0, 8)} created.`,
      });
    } catch (e) {
      toast.error("Export failed", { description: String(e.message || e) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl bg-[var(--st-panel)] border border-[var(--st-border)] rounded-none p-0" data-testid="export-panel">
        <DialogHeader className="px-6 pt-6 pb-3 border-b border-[var(--st-border)]">
          <DialogTitle className="text-base font-medium tracking-tight">
            EXPORT / HANDOFF
          </DialogTitle>
          <DialogDescription className="font-mono text-[11px] text-[var(--st-text-muted)] uppercase tracking-wider">
            PROFILE :: {profileName}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-3 px-6 py-5">
          {Object.entries(targets).map(([key, t]) => {
            const Icon = ICONS[key] || FileCog;
            return (
              <div key={key} className="st-panel-raised p-4 flex flex-col gap-3" data-testid={`export-target-${key}`}>
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 border border-[var(--st-border)] flex items-center justify-center">
                    <Icon className="w-5 h-5 text-[var(--st-accent)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-[var(--st-text)] truncate">{t.name}</div>
                    <div className="text-xs text-[var(--st-text-secondary)] mt-0.5">{t.description}</div>
                    <div className="font-mono text-[9px] text-[var(--st-text-muted)] uppercase tracking-wider mt-1">
                      FORMAT :: {t.format}
                    </div>
                  </div>
                </div>
                <Button
                  variant="outline"
                  className="rounded-none border-[var(--st-accent)] text-[var(--st-accent)] hover:bg-[var(--st-accent-deep)]/30 font-mono text-[11px] uppercase tracking-widest h-9"
                  disabled={busy === key}
                  onClick={() => handleExport(key)}
                  data-testid={`export-btn-${key}`}
                >
                  {busy === key ? "HANDING OFF…" : `Send to ${t.name}`}
                </Button>
              </div>
            );
          })}
        </div>

        <div className="border-t border-[var(--st-border)] px-6 py-4 bg-[var(--st-panel-deep)]">
          <div className="st-data-label mb-2">HANDOFF LOG</div>
          <pre
            data-testid="export-log"
            className="font-mono text-[11px] leading-relaxed text-[var(--st-text-secondary)] max-h-44 overflow-auto whitespace-pre-wrap"
          >
{log.length ? log.join("\n") : "[ idle ] no handoffs in this session"}
          </pre>
        </div>

        {artifact && (
          <div className="border-t border-[var(--st-border)] px-6 py-4 bg-[var(--st-panel)]">
            <div className="st-data-label mb-2">LAST ARTIFACT PREVIEW (truncated)</div>
            <pre data-testid="export-artifact-preview" className="font-mono text-[10px] text-[var(--st-text-secondary)] max-h-40 overflow-auto bg-[var(--st-panel-deep)] p-3 border border-[var(--st-border)]">
{JSON.stringify({
  artifact_id: artifact.artifact_id,
  target: artifact.target_name,
  format: artifact.format,
  profile: artifact.profile_name,
  tune_summary: artifact.tune_summary,
  engine: artifact.engine_metadata,
}, null, 2)}
            </pre>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
