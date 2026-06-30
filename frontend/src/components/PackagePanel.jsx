import React, { useEffect, useRef, useState } from "react";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  downloadPackageUrl, duplicatePackage, renamePackage,
  addPackageNote, deletePackageNote, getPackage,
} from "@/lib/api";
import { Copy, Download, FileText, Pencil, Save, Trash2, Package as PackageIcon, X } from "lucide-react";
import { toast } from "sonner";
import { fmt } from "@/lib/format";

const inputCls = "rounded-none bg-[var(--st-panel-deep)] border-[var(--st-border)] focus-visible:ring-0 focus-visible:border-[var(--st-accent)] h-9 font-mono text-sm";

export default function PackagePanel({ packageId, profile, onRefresh, onDuplicated }) {
  const [pkg, setPkg] = useState(null);
  const [renameVal, setRenameVal] = useState("");
  const [editingName, setEditingName] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [posting, setPosting] = useState(false);

  const load = () => getPackage(packageId).then(setPkg);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [packageId, profile?.updated_at]);

  if (!pkg) {
    return (
      <Panel testId="package-panel-loading">
        <div className="font-mono text-xs text-[var(--st-text-muted)] py-6 text-center uppercase tracking-widest">
          LOADING PACKAGE METADATA…
        </div>
      </Panel>
    );
  }

  const meta = pkg.package_metadata;
  const cal = pkg.calibration;
  const tables = ["fuel_table", "ignition_table", "afr_target_table", "boost_target_table",
                   "idle_tables", "cold_start_tables", "ve_curve"];

  const onDownload = () => {
    const url = downloadPackageUrl(packageId);
    const a = document.createElement("a");
    a.href = url;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success("Package download started", { description: `${meta.name}.sacp` });
  };

  const onDuplicate = async () => {
    const dup = await duplicatePackage(packageId);
    toast.success("Package duplicated", { description: dup.package_metadata.name });
    if (onDuplicated) onDuplicated(dup.package_metadata.package_id);
  };

  const submitRename = async () => {
    const newName = renameVal.trim();
    if (!newName) return;
    await renamePackage(packageId, newName);
    toast.success("Package renamed");
    setEditingName(false);
    setRenameVal("");
    if (onRefresh) onRefresh();
    load();
  };

  const submitNote = async () => {
    const text = noteText.trim();
    if (!text) return;
    setPosting(true);
    try {
      await addPackageNote(packageId, text);
      toast.success("Note added");
      setNoteText("");
      load();
    } finally {
      setPosting(false);
    }
  };

  const removeNote = async (noteId) => {
    await deletePackageNote(packageId, noteId);
    toast.success("Note removed");
    load();
  };

  return (
    <div className="space-y-4" data-testid="package-panel">
      {/* SACP header card */}
      <Panel testId="package-meta-card">
        <PanelHeader
          label="STANDAILONE CALIBRATION PACKAGE"
          sub={`SCHEMA v${meta.schema_version}`}
          right={
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={onDownload} data-testid="package-download-btn"
                      className="rounded-none border-[var(--st-accent)] text-[var(--st-accent)] hover:bg-[var(--st-accent-deep)]/30 font-mono text-[10px] uppercase tracking-widest h-8">
                <Download className="w-3 h-3 mr-1.5" /> Download .sacp
              </Button>
              <Button variant="outline" size="sm" onClick={onDuplicate} data-testid="package-duplicate-btn"
                      className="rounded-none border-[var(--st-border)] hover:border-[var(--st-accent)] hover:text-[var(--st-accent)] font-mono text-[10px] uppercase tracking-widest h-8">
                <Copy className="w-3 h-3 mr-1.5" /> Duplicate
              </Button>
            </div>
          }
        />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <Field label="PACKAGE ID" value={meta.package_id.slice(0, 8)} mono />
          <Field label="STATUS" value={meta.status} />
          <Field label="ORIGIN" value={meta.origin_application} />
          <Field label="GENERATOR" value={meta.generator_version} />
          <Field label="CREATED" value={fmt.date(meta.created_at)} />
          <Field label="LAST MODIFIED" value={fmt.date(meta.last_modified_at)} />
          <Field label="CHECKSUM" value={(meta.checksum || "—").replace("sha256:", "").slice(0, 16)} mono testId="meta-checksum" />
          <Field label="EXTENSIONS" value={meta.extensions.join(" · ")} mono />
        </div>

        {/* Rename row */}
        <div className="flex items-center gap-2 border-t border-[var(--st-border)] pt-3">
          <span className="st-data-label">NAME</span>
          {editingName ? (
            <>
              <Input
                data-testid="package-rename-input"
                value={renameVal}
                onChange={(e) => setRenameVal(e.target.value)}
                placeholder={meta.name}
                className={`${inputCls} flex-1 max-w-md`}
                autoFocus
              />
              <Button size="sm" onClick={submitRename} data-testid="package-rename-save"
                      className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-[10px] uppercase tracking-widest h-8">
                <Save className="w-3 h-3 mr-1.5" /> Save
              </Button>
              <button onClick={() => setEditingName(false)} className="text-[var(--st-text-muted)] hover:text-[var(--st-text)]" data-testid="package-rename-cancel">
                <X className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <span className="font-mono text-sm text-[var(--st-text)] flex-1 truncate" data-testid="package-name">{meta.name}</span>
              <button onClick={() => { setEditingName(true); setRenameVal(meta.name); }}
                      className="font-mono text-[10px] text-[var(--st-text-muted)] hover:text-[var(--st-accent)] flex items-center gap-1 uppercase tracking-widest"
                      data-testid="package-rename-edit">
                <Pencil className="w-3 h-3" /> Edit
              </button>
            </>
          )}
        </div>
      </Panel>

      {/* Calibration tables present */}
      <Panel testId="package-cal-summary">
        <PanelHeader label="CALIBRATION SECTION" sub="TABLES PRESENT IN PACKAGE" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
          {tables.map((k) => {
            const t = cal[k];
            const has = !!t && (Array.isArray(t) ? t.length > 0 : Object.keys(t).length > 0);
            const dim = (t && t.metadata) ? `${t.metadata.rows}×${t.metadata.cols}` : "";
            const conf = (t && t.metadata) ? `${Math.round((t.metadata.confidence || 0) * 100)}%` : "";
            return (
              <div key={k}
                   data-testid={`cal-section-${k}`}
                   className={`border ${has ? "border-[var(--st-border)]" : "border-dashed border-[var(--st-border)] opacity-50"} bg-[var(--st-panel-deep)] p-3`}>
                <div className="st-data-label truncate">{k.replace(/_/g, " ").toUpperCase()}</div>
                <div className="font-mono text-sm mt-1">{has ? "PRESENT" : "—"}</div>
                {has && dim && <div className="font-mono text-[10px] text-[var(--st-text-muted)] mt-1">{dim} · conf {conf}</div>}
              </div>
            );
          })}
        </div>
      </Panel>

      {/* Telemetry assumptions snapshot */}
      <Panel testId="package-telemetry">
        <PanelHeader label="TELEMETRY ASSUMPTIONS" sub="DIAG-SIM BASELINE" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Field label="EXP. IDLE RPM" value={pkg.telemetry_assumptions.expected_idle_rpm || "—"} />
          <Field label="EXP. CRUISE AFR" value={pkg.telemetry_assumptions.expected_cruise_afr || "—"} />
          <Field label="EXP. INJ DUTY" value={pkg.telemetry_assumptions.expected_injector_duty_pct
                                              ? `${Math.round(pkg.telemetry_assumptions.expected_injector_duty_pct)}%` : "—"} />
          <Field label="EXP. KNOCK" value={pkg.telemetry_assumptions.expected_knock_activity?.toUpperCase() || "—"} />
          <Field label="IAT RANGE" value={`${pkg.telemetry_assumptions.expected_iat_range_c[0]} – ${pkg.telemetry_assumptions.expected_iat_range_c[1]} °C`} />
          <Field label="ECT RANGE" value={`${pkg.telemetry_assumptions.expected_coolant_range_c[0]} – ${pkg.telemetry_assumptions.expected_coolant_range_c[1]} °C`} />
          <Field label="LAMBDA RANGE" value={`${pkg.telemetry_assumptions.expected_lambda_range[0]} – ${pkg.telemetry_assumptions.expected_lambda_range[1]}`} />
          <Field label="FUEL PRESS." value={pkg.telemetry_assumptions.expected_fuel_pressure_bar
                                            ? `${pkg.telemetry_assumptions.expected_fuel_pressure_bar} bar` : "—"} />
        </div>
      </Panel>

      {/* Notes */}
      <Panel testId="package-notes">
        <PanelHeader label="ENGINEERING NOTES" sub={`${pkg.notes.length} ENTRIES`}
                     right={<FileText className="w-4 h-4 text-[var(--st-text-muted)]" />} />
        <div className="flex gap-2 mb-3">
          <Textarea
            data-testid="note-input"
            placeholder="Add a free-form engineering note (max 4000 chars)…"
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            rows={2}
            className="rounded-none bg-[var(--st-panel-deep)] border-[var(--st-border)] focus-visible:ring-0 focus-visible:border-[var(--st-accent)] font-mono text-sm resize-none"
          />
          <Button onClick={submitNote} disabled={posting || !noteText.trim()} data-testid="note-add-btn"
                  className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs uppercase tracking-widest self-start">
            <Save className="w-3.5 h-3.5 mr-1.5" /> Add
          </Button>
        </div>
        {pkg.notes.length === 0 ? (
          <div className="font-mono text-xs text-[var(--st-text-muted)] py-4 text-center uppercase tracking-widest">
            [ idle ] no engineering notes recorded
          </div>
        ) : (
          <div className="space-y-2">
            {pkg.notes.slice().reverse().map((n) => (
              <div key={n.note_id} data-testid={`note-${n.note_id}`}
                   className="border border-[var(--st-border)] bg-[var(--st-panel-deep)] p-3 flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-[10px] text-[var(--st-text-muted)] uppercase tracking-widest mb-1">
                    {n.author} · {fmt.date(n.created_at)}
                  </div>
                  <div className="text-sm text-[var(--st-text)] whitespace-pre-wrap break-words">{n.text}</div>
                </div>
                <button onClick={() => removeNote(n.note_id)} className="text-[var(--st-text-muted)] hover:text-[var(--st-danger)]"
                        data-testid={`note-delete-${n.note_id}`}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function Field({ label, value, mono = false, testId }) {
  return (
    <div className="border border-[var(--st-border)] bg-[var(--st-panel-deep)] p-3" data-testid={testId}>
      <div className="st-data-label">{label}</div>
      <div className={`text-sm mt-1 ${mono ? "font-mono tabular-nums" : ""}`}>{value || "—"}</div>
    </div>
  );
}

/** Import .sacp file dialog button — for use in Dashboard. */
export function ImportPackageButton({ onImported }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const text = await file.text();
      const payload = JSON.parse(text);
      const { uploadPackage: doUpload } = await import("@/lib/api");
      const pkg = await doUpload(payload);
      toast.success("Package imported", { description: pkg.package_metadata.name });
      if (onImported) onImported(pkg.package_metadata.package_id);
    } catch (e) {
      toast.error("Import failed", { description: String(e.message || e) });
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <>
      <input
        type="file"
        ref={inputRef}
        data-testid="import-sacp-file-input"
        accept=".sacp,.standalone,.json,application/json,application/x-sacp+json"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <Button
        variant="outline"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        data-testid="import-sacp-btn"
        className="rounded-none border-[var(--st-border)] hover:border-[var(--st-accent)] hover:text-[var(--st-accent)] font-mono text-xs uppercase tracking-widest h-12 px-5"
      >
        <PackageIcon className="w-4 h-4 mr-2" />
        {busy ? "IMPORTING…" : "Import .sacp"}
      </Button>
    </>
  );
}
