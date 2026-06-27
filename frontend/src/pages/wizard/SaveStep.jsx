import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createProfile } from "@/lib/api";
import { toast } from "sonner";
import { ArrowLeft, Check, AlertOctagon } from "lucide-react";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import { fmt } from "@/lib/format";

export default function SaveStep({ intake, tune, adjustments, onBack }) {
  const [name, setName] = useState(
    `${intake.displacement_l}L ${intake.cylinders}cyl ${intake.induction} · ${intake.target_hp}hp`
  );
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const onSave = async () => {
    if (!name.trim()) {
      toast.error("Profile name required");
      return;
    }
    if (!tune) {
      toast.error("No tune package available");
      return;
    }
    setSaving(true);
    try {
      const profile = await createProfile({
        name: name.trim(),
        intake,
        tune_package: tune,
        adjustments,
        vehicle_metadata: {
          drivetrain: intake.drivetrain,
          transmission: intake.transmission,
          intended_use: intake.intended_use,
        },
      });
      toast.success("Profile created", {
        description: `${profile.name} saved with starter tune.`,
      });
      navigate(`/profiles/${profile.id}`);
    } catch (e) {
      toast.error("Save failed", { description: String(e.message || e) });
    } finally {
      setSaving(false);
    }
  };

  if (!tune) {
    return (
      <div className="text-center py-12 font-mono text-xs text-[var(--st-text-muted)] uppercase tracking-widest">
        NO TUNE PACKAGE — RETURN TO STEP 3
      </div>
    );
  }

  const dangerCount = tune.safety_envelope.warnings.filter((w) => w.level === "danger").length;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="save-step">
      <div className="lg:col-span-2 flex flex-col gap-4">
        <Panel testId="save-panel">
          <PanelHeader index={5} label="STEP 05 // SAVE TO PROFILE" sub="FINALIZE STARTER TUNE" />
          <div className="space-y-5 max-w-xl">
            <div>
              <Label className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-text-secondary)]">
                PROFILE NAME
              </Label>
              <Input
                data-testid="profile-name-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="rounded-none bg-[var(--st-panel-deep)] border-[var(--st-border)] focus-visible:ring-0 focus-visible:border-[var(--st-accent)] h-10 font-mono text-sm mt-2"
              />
            </div>

            {dangerCount > 0 && (
              <div className="border border-[var(--st-danger)] bg-[#7f1d1d]/20 p-3 flex items-start gap-3" data-testid="save-danger-warning">
                <AlertOctagon className="w-4 h-4 mt-0.5 text-[var(--st-danger)]" />
                <p className="text-xs text-[var(--st-text)] leading-relaxed">
                  This tune package contains <strong>{dangerCount}</strong> critical safety warning(s).
                  You can still save it, but the calibration should be re-evaluated before any vehicle
                  is run on it. Consider adjusting target HP or hardware in Step 1.
                </p>
              </div>
            )}

            <div className="bg-[var(--st-panel-deep)] border border-[var(--st-border)] p-4">
              <div className="st-panel-title mb-3">PROFILE SUMMARY</div>
              <div className="grid grid-cols-2 gap-y-2 gap-x-6 font-mono text-xs">
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">ENGINE</span>
                  <span>{intake.displacement_l}L · {intake.cylinders}cyl · {intake.induction}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">FUEL</span>
                  <span>{intake.fuel_type}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">TARGET HP</span>
                  <span>{fmt.hp(intake.target_hp)}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">REV LIMIT</span>
                  <span>{intake.rev_limit} RPM</span>
                </div>
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">IGN CEILING</span>
                  <span>{fmt.deg(tune.safety_envelope.ignition_ceiling)}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">BOOST CEILING</span>
                  <span>{tune.safety_envelope.boost_ceiling_kpa ? fmt.kpa(tune.safety_envelope.boost_ceiling_kpa) : "—"}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">FUEL CELLS</span>
                  <span>{tune.fuel_map_ms.length * tune.fuel_map_ms[0].length}</span>
                </div>
                <div className="flex justify-between border-b border-[var(--st-border)] py-1">
                  <span className="text-[var(--st-text-muted)]">IGN CELLS</span>
                  <span>{tune.ignition_map_deg.length * tune.ignition_map_deg[0].length}</span>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <ConfidenceBadge value={tune.confidence.overall} label="OVERALL" testId="save-conf-overall" />
              <ConfidenceBadge value={tune.confidence.fuel} label="FUEL" />
              <ConfidenceBadge value={tune.confidence.ignition} label="IGN" />
              <ConfidenceBadge value={tune.confidence.safety} label="SAFETY" />
            </div>
          </div>
        </Panel>

        <div className="flex items-center justify-between gap-3 mt-2">
          <Button variant="ghost" onClick={onBack} data-testid="save-back-btn"
                  className="rounded-none font-mono text-xs uppercase tracking-widest text-[var(--st-text-muted)] hover:text-[var(--st-text)]">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to review
          </Button>
          <Button onClick={onSave} disabled={saving} data-testid="create-profile-btn"
                  className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs uppercase tracking-widest h-11 px-6">
            <Check className="w-4 h-4 mr-2" />
            {saving ? "Creating Profile…" : "Create Profile with This Tune"}
          </Button>
        </div>
      </div>

      <Panel raised testId="save-next-steps">
        <PanelHeader label="WHAT HAPPENS NEXT" />
        <ol className="text-xs text-[var(--st-text-secondary)] space-y-3 leading-relaxed list-decimal list-inside">
          <li>Generated maps, idle / cold start tables and the safety envelope are persisted to the profile.</li>
          <li>The full generation history is preserved for undo and comparison against future regenerations.</li>
          <li>You can then hand off the tune to <strong className="text-[var(--st-text)]">DIAG-SIM</strong>, <strong className="text-[var(--st-text)]">Tune Inspector Pro</strong>, <strong className="text-[var(--st-text)]">Forensic Inspector</strong>, or export a structured artifact for ECU flashing.</li>
          <li>Future refinements (auto-retune, AI-assisted calibration) will build on this starter profile.</li>
        </ol>
      </Panel>
    </div>
  );
}
