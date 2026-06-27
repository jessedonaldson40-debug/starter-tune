import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Activity, FileSearch, ScanLine, FileCog, ExternalLink, Download as DownloadIcon, Check } from "lucide-react";
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
  const [artifacts, setArtifacts] = useState([]);  // all artifacts produced this session
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    listExportTargets().then(setTargets).catch(() => {});
  }, [open]);

  // Reset when the modal is closed
  useEffect(() => {
    if (!open) {
      setBusy(null);
    }
  }, [open]);

  const downloadEcuArtifact = (art) => {
    const blob = new Blob([JSON.stringify(art, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${profileName.replace(/[^a-z0-9]+/gi, "_")}_${art.artifact_id.slice(0, 8)}.ecuflash.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExport = async (key) => {
    setBusy(key);
    try {
      const res = await exportProfile(profileId, key);
      setArtifacts((prev) => [res, ...prev]);
      setLog((prev) => [
        `[${fmt.date(res.generated_at)}] HANDOFF :: ${res.target_name}`,
        `  artifact_id     ${res.artifact_id}`,
        `  format          ${res.format}`,
        `  fuel_cells      ${res.tune_summary.fuel_cells}`,
        `  ignition_cells  ${res.tune_summary.ignition_cells}`,
        `  confidence      ${(res.tune_summary.confidence_overall * 100).toFixed(0)}%`,
        `  warnings        ${res.tune_summary.warnings_count}`,
        `  source_gen_idx  ${res.source_generation_index}`,
        res.deep_link ? `  deep_link       ${res.deep_link}` : "  deep_link       —",
        "",
        ...prev,
      ]);

      if (key === "ecu") {
        downloadEcuArtifact(res);
        toast.success("ECU artifact downloaded", {
          description: `Saved ${res.artifact_id.slice(0, 8)}.ecuflash.json`,
        });
      } else {
        toast.success(`${res.target_name} handoff complete`, {
          description: res.deep_link
            ? "Click the OPEN button below to view, or run more handoffs."
            : `Artifact ${res.artifact_id.slice(0, 8)} created.`,
        });
      }
    } catch (e) {
      toast.error("Export failed", { description: String(e.message || e) });
    } finally {
      setBusy(null);
    }
  };

  const openArtifact = (art) => {
    if (!art.deep_link) return;
    onOpenChange(false);
    navigate(art.deep_link);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl bg-[var(--st-panel)] border border-[var(--st-border)] rounded-none p-0 max-h-[88vh] overflow-y-auto" data-testid="export-panel">
        <DialogHeader className="px-6 pt-6 pb-3 border-b border-[var(--st-border)] sticky top-0 bg-[var(--st-panel)] z-10">
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
            const isEcu = key === "ecu";
            const count = artifacts.filter((a) => a.target === key).length;
            return (
              <div key={key} className="st-panel-raised p-4 flex flex-col gap-3" data-testid={`export-target-${key}`}>
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 border border-[var(--st-border)] flex items-center justify-center">
                    <Icon className="w-5 h-5 text-[var(--st-accent)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="text-sm text-[var(--st-text)] truncate">{t.name}</div>
                      {count > 0 && (
                        <span className="font-mono text-[9px] text-[var(--st-safe)] uppercase tracking-widest border border-[var(--st-safe)] px-1.5 py-0.5">
                          ×{count}
                        </span>
                      )}
                    </div>
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
                  {busy === key ? (
                    "HANDING OFF…"
                  ) : isEcu ? (
                    <><DownloadIcon className="w-3.5 h-3.5 mr-2" /> {count > 0 ? "Re-download" : "Download Artifact"}</>
                  ) : (
                    <><ExternalLink className="w-3.5 h-3.5 mr-2" /> {count > 0 ? `Run again` : `Send to ${t.name}`}</>
                  )}
                </Button>
              </div>
            );
          })}
        </div>

        {/* Per-artifact action list — built up across the modal session */}
        {artifacts.length > 0 && (
          <div className="border-t border-[var(--st-border)] px-6 py-4 bg-[var(--st-panel)]" data-testid="artifact-actions-list">
            <div className="st-data-label mb-2">SESSION ARTIFACTS · {artifacts.length}</div>
            <div className="space-y-2">
              {artifacts.map((a) => (
                <div key={a.artifact_id}
                     className="border border-[var(--st-border)] p-3 flex items-center justify-between gap-3"
                     data-testid={`artifact-row-${a.target}-${a.artifact_id}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <Check className="w-3.5 h-3.5 text-[var(--st-safe)] shrink-0" />
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] uppercase tracking-widest text-[var(--st-text)] truncate">
                        {a.target_name}
                      </div>
                      <div className="font-mono text-[10px] text-[var(--st-text-muted)] truncate">
                        {a.artifact_id.slice(0, 8)} · {fmt.date(a.generated_at)}
                      </div>
                    </div>
                  </div>
                  {a.deep_link ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openArtifact(a)}
                      data-testid={`artifact-open-${a.target}-${a.artifact_id}`}
                      className="rounded-none border-[var(--st-accent)] text-[var(--st-accent)] hover:bg-[var(--st-accent-deep)]/30 font-mono text-[10px] uppercase tracking-widest h-7"
                    >
                      OPEN <ExternalLink className="w-3 h-3 ml-1.5" />
                    </Button>
                  ) : a.target === "ecu" ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => downloadEcuArtifact(a)}
                      data-testid={`artifact-download-${a.artifact_id}`}
                      className="rounded-none border-[var(--st-border)] hover:border-[var(--st-accent)] hover:text-[var(--st-accent)] font-mono text-[10px] uppercase tracking-widest h-7"
                    >
                      DOWNLOAD <DownloadIcon className="w-3 h-3 ml-1.5" />
                    </Button>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="border-t border-[var(--st-border)] px-6 py-4 bg-[var(--st-panel-deep)]">
          <div className="st-data-label mb-2">HANDOFF LOG</div>
          <pre
            data-testid="export-log"
            className="font-mono text-[11px] leading-relaxed text-[var(--st-text-secondary)] max-h-44 overflow-auto whitespace-pre-wrap"
          >
{log.length ? log.join("\n") : "[ idle ] no handoffs in this session"}
          </pre>
        </div>
      </DialogContent>
    </Dialog>
  );
}
