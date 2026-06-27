import React, { useEffect, useState } from "react";
import { Panel, PanelHeader } from "@/components/PanelHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { predictHp, vePreview } from "@/lib/api";
import { fmt } from "@/lib/format";
import { ChevronDown, ChevronUp, Info, ArrowRight } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, YAxis, XAxis, Tooltip as RTooltip } from "recharts";

const FUEL_OPTS = ["91", "93", "98", "E85", "Methanol", "Flex"];
const INDUCTION_OPTS = ["NA", "Turbo", "Supercharged"];
const INTERCOOLER_OPTS = ["None", "Stock", "Upgraded", "Race"];
const USE_OPTS = ["street", "daily", "mixed", "drag", "track", "towing"];
const TURBO_CLASS_OPTS = [
  "Small frame (~52mm)",
  "Medium frame (~64mm)",
  "Large frame (~72mm)",
  "Twin small (~52mm x2)",
  "Big single (>80mm)",
];

const HARDWARE_PRESETS = {
  "Custom": null,
  "Honda K20 (NA street)": { displacement_l: 2.0, cylinders: 4, induction: "NA", fuel_type: "93", target_hp: 220, rev_limit: 8200, injector_cc: 310, compression_ratio: 11.0 },
  "Subaru EJ257 (turbo street)": { displacement_l: 2.5, cylinders: 4, induction: "Turbo", fuel_type: "93", target_hp: 320, rev_limit: 6800, injector_cc: 565, compression_ratio: 8.2 },
  "LS3 6.2 (NA)": { displacement_l: 6.2, cylinders: 8, induction: "NA", fuel_type: "93", target_hp: 480, rev_limit: 6600, injector_cc: 440, compression_ratio: 10.7 },
  "B58 (turbo I6)": { displacement_l: 3.0, cylinders: 6, induction: "Turbo", fuel_type: "93", target_hp: 480, rev_limit: 7000, injector_cc: 525, compression_ratio: 11.0 },
  "2JZ-GTE (big turbo)": { displacement_l: 3.0, cylinders: 6, induction: "Turbo", fuel_type: "E85", target_hp: 700, rev_limit: 7800, injector_cc: 1050, compression_ratio: 8.5 },
};

function FieldGroup({ label, hint, children, testId }) {
  return (
    <div className="flex flex-col gap-1.5" data-testid={testId}>
      <div className="flex items-center justify-between">
        <Label className="font-mono text-[10px] uppercase tracking-widest text-[var(--st-text-secondary)]">
          {label}
        </Label>
        {hint && (
          <span className="text-[10px] text-[var(--st-text-muted)] font-mono italic">{hint}</span>
        )}
      </div>
      {children}
    </div>
  );
}

const inputCls = "rounded-none bg-[var(--st-panel-deep)] border-[var(--st-border)] focus-visible:ring-0 focus-visible:border-[var(--st-accent)] h-9 font-mono text-sm";
const selectTriggerCls = "rounded-none bg-[var(--st-panel-deep)] border-[var(--st-border)] focus:ring-0 focus-visible:ring-0 focus-visible:border-[var(--st-accent)] h-9 font-mono text-sm";

export default function IntakeStep({ intake, setIntake, onNext, onCancel }) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [predicted, setPredicted] = useState(null);
  const [veCurve, setVeCurve] = useState([]);
  const [preset, setPreset] = useState("Custom");

  const update = (patch) => setIntake((p) => ({ ...p, ...patch }));

  // Debounced live preview
  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const [pred, ve] = await Promise.all([predictHp(intake), vePreview(intake)]);
        setPredicted(pred);
        setVeCurve(ve.ve_curve);
      } catch (e) { /* ignore */ }
    }, 350);
    return () => clearTimeout(t);
  }, [intake.displacement_l, intake.cylinders, intake.induction, intake.fuel_type, intake.rev_limit]);

  const applyPreset = (name) => {
    setPreset(name);
    if (HARDWARE_PRESETS[name]) {
      update({ ...HARDWARE_PRESETS[name], hardware_preset: name });
    }
  };

  const boosted = intake.induction !== "NA";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="intake-step">
      {/* LEFT: Form */}
      <div className="lg:col-span-2 flex flex-col gap-4">
        <Panel testId="intake-core-panel">
          <PanelHeader index={1} label="STEP 01 // ENGINE SPEC INTAKE" sub="REQUIRED FIELDS" />
          <p className="text-xs text-[var(--st-text-secondary)] mb-4 leading-relaxed">
            Enter minimal engine metadata. The generator will produce a complete conservative
            calibration package — fuel, ignition, idle, cold start, and boost targets — bounded by
            a computed safety envelope.
          </p>

          <FieldGroup label="HARDWARE PRESET" hint="Quick-start template" testId="field-preset">
            <Select value={preset} onValueChange={applyPreset}>
              <SelectTrigger className={selectTriggerCls} data-testid="select-preset"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                {Object.keys(HARDWARE_PRESETS).map((k) => (
                  <SelectItem key={k} value={k} className="rounded-none font-mono text-xs">{k}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FieldGroup>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-5">
            <FieldGroup label="DISPLACEMENT (L)" testId="field-displacement">
              <Input data-testid="input-displacement" type="number" step="0.1" min="0.5" max="12"
                     className={inputCls}
                     value={intake.displacement_l}
                     onChange={(e) => update({ displacement_l: parseFloat(e.target.value || 0) })} />
            </FieldGroup>
            <FieldGroup label="CYLINDERS" testId="field-cylinders">
              <Input data-testid="input-cylinders" type="number" step="1" min="2" max="16"
                     className={inputCls}
                     value={intake.cylinders}
                     onChange={(e) => update({ cylinders: parseInt(e.target.value || 0) })} />
            </FieldGroup>
            <FieldGroup label="INDUCTION" testId="field-induction">
              <Select value={intake.induction} onValueChange={(v) => update({ induction: v })}>
                <SelectTrigger className={selectTriggerCls} data-testid="select-induction"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                  {INDUCTION_OPTS.map((o) => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                </SelectContent>
              </Select>
            </FieldGroup>
            <FieldGroup label="FUEL TYPE" testId="field-fuel">
              <Select value={intake.fuel_type} onValueChange={(v) => update({ fuel_type: v })}>
                <SelectTrigger className={selectTriggerCls} data-testid="select-fuel"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                  {FUEL_OPTS.map((o) => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                </SelectContent>
              </Select>
            </FieldGroup>
            <FieldGroup label="TARGET HORSEPOWER" testId="field-target-hp">
              <Input data-testid="input-target-hp" type="number" step="10" min="50" max="2500"
                     className={inputCls}
                     value={intake.target_hp}
                     onChange={(e) => update({ target_hp: parseInt(e.target.value || 0) })} />
            </FieldGroup>
            <FieldGroup label="REV LIMIT (RPM)" testId="field-rev-limit">
              <Input data-testid="input-rev-limit" type="number" step="100" min="4000" max="11000"
                     className={inputCls}
                     value={intake.rev_limit}
                     onChange={(e) => update({ rev_limit: parseInt(e.target.value || 0) })} />
            </FieldGroup>
          </div>

          {boosted && intake.fuel_type === "Flex" && (
            <FieldGroup label="ETHANOL CONTENT (%)" hint="Flex fuel blend" testId="field-ethanol">
              <Input data-testid="input-ethanol" type="number" step="5" min="0" max="100"
                     className={inputCls}
                     value={intake.ethanol_pct ?? ""}
                     onChange={(e) => update({ ethanol_pct: e.target.value === "" ? null : parseInt(e.target.value) })} />
            </FieldGroup>
          )}
        </Panel>

        {/* Advanced */}
        <Panel testId="intake-advanced-panel">
          <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
            <CollapsibleTrigger asChild>
              <button className="w-full flex items-center justify-between" data-testid="advanced-toggle">
                <div>
                  <span className="st-panel-title">ADVANCED SETTINGS</span>
                  <span className="font-mono text-[10px] text-[var(--st-text-muted)] ml-3">OPTIONAL · IMPROVES CONFIDENCE</span>
                </div>
                {advancedOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-4">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <FieldGroup label="INJECTOR SIZE (cc/min)" testId="field-injector">
                  <Input data-testid="input-injector" type="number" step="10" className={inputCls}
                         value={intake.injector_cc ?? ""}
                         onChange={(e) => update({ injector_cc: e.target.value === "" ? null : parseInt(e.target.value) })} />
                </FieldGroup>
                <FieldGroup label="MAP SENSOR (kPa)" testId="field-map-sensor">
                  <Input data-testid="input-map-sensor" type="number" step="10" className={inputCls}
                         value={intake.map_sensor_kpa ?? ""}
                         onChange={(e) => update({ map_sensor_kpa: e.target.value === "" ? null : parseInt(e.target.value) })} />
                </FieldGroup>
                <FieldGroup label="COMPRESSION RATIO" testId="field-compression">
                  <Input data-testid="input-compression" type="number" step="0.1" className={inputCls}
                         value={intake.compression_ratio ?? ""}
                         onChange={(e) => update({ compression_ratio: e.target.value === "" ? null : parseFloat(e.target.value) })} />
                </FieldGroup>
                <FieldGroup label="INDUCTION STRATEGY" testId="field-strategy">
                  <Select value={intake.induction_strategy} onValueChange={(v) => update({ induction_strategy: v })}>
                    <SelectTrigger className={selectTriggerCls} data-testid="select-strategy"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                      <SelectItem value="SD" className="rounded-none font-mono text-xs">Speed Density</SelectItem>
                      <SelectItem value="MAF" className="rounded-none font-mono text-xs">MAF</SelectItem>
                      <SelectItem value="Alpha-N" className="rounded-none font-mono text-xs">Alpha-N</SelectItem>
                    </SelectContent>
                  </Select>
                </FieldGroup>
                <FieldGroup label="INTENDED USE" testId="field-use">
                  <Select value={intake.intended_use} onValueChange={(v) => update({ intended_use: v })}>
                    <SelectTrigger className={selectTriggerCls} data-testid="select-use"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                      {USE_OPTS.map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </FieldGroup>
                <FieldGroup label="DRIVETRAIN" testId="field-drivetrain">
                  <Select value={intake.drivetrain || ""} onValueChange={(v) => update({ drivetrain: v })}>
                    <SelectTrigger className={selectTriggerCls} data-testid="select-drivetrain"><SelectValue placeholder="—" /></SelectTrigger>
                    <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                      {["FWD","RWD","AWD","4WD"].map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </FieldGroup>
                <FieldGroup label="TRANSMISSION" testId="field-trans">
                  <Select value={intake.transmission || ""} onValueChange={(v) => update({ transmission: v })}>
                    <SelectTrigger className={selectTriggerCls} data-testid="select-trans"><SelectValue placeholder="—" /></SelectTrigger>
                    <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                      {["Manual","Automatic","DCT","CVT","Sequential"].map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </FieldGroup>
                {boosted && (
                  <>
                    <FieldGroup label="TURBO CLASS" testId="field-turbo-class">
                      <Select value={intake.turbo_class || ""} onValueChange={(v) => update({ turbo_class: v })}>
                        <SelectTrigger className={selectTriggerCls} data-testid="select-turbo-class"><SelectValue placeholder="—" /></SelectTrigger>
                        <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                          {TURBO_CLASS_OPTS.map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </FieldGroup>
                    <FieldGroup label="SPOOL RPM" testId="field-spool">
                      <Input data-testid="input-spool" type="number" step="100" className={inputCls}
                             value={intake.spool_rpm}
                             onChange={(e) => update({ spool_rpm: parseInt(e.target.value || 0) })} />
                    </FieldGroup>
                    <FieldGroup label="INTERCOOLER" testId="field-ic">
                      <Select value={intake.intercooler_class} onValueChange={(v) => update({ intercooler_class: v })}>
                        <SelectTrigger className={selectTriggerCls} data-testid="select-ic"><SelectValue /></SelectTrigger>
                        <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                          {INTERCOOLER_OPTS.map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </FieldGroup>
                  </>
                )}
                <FieldGroup label="IDLE QUALITY" testId="field-idle-q">
                  <Select value={intake.idle_quality} onValueChange={(v) => update({ idle_quality: v })}>
                    <SelectTrigger className={selectTriggerCls} data-testid="select-idle-q"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                      {["smooth","balanced","aggressive"].map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </FieldGroup>
                <FieldGroup label="DRIVABILITY PRIORITY" testId="field-drive-q">
                  <Select value={intake.drivability_priority} onValueChange={(v) => update({ drivability_priority: v })}>
                    <SelectTrigger className={selectTriggerCls} data-testid="select-drive-q"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                      {["drivability","balanced","performance"].map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </FieldGroup>
                <FieldGroup label="CLIMATE BIAS" testId="field-climate">
                  <Select value={intake.climate} onValueChange={(v) => update({ climate: v })}>
                    <SelectTrigger className={selectTriggerCls} data-testid="select-climate"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-[var(--st-panel)] border-[var(--st-border)] rounded-none">
                      {["cold","temperate","hot","alpine"].map(o => <SelectItem key={o} value={o} className="rounded-none font-mono text-xs">{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </FieldGroup>
              </div>
            </CollapsibleContent>
          </Collapsible>
        </Panel>

        <div className="flex items-center justify-between gap-3 mt-2">
          <Button variant="ghost" onClick={onCancel} data-testid="intake-cancel-btn"
                  className="rounded-none font-mono text-xs uppercase tracking-widest text-[var(--st-text-muted)] hover:text-[var(--st-text)]">
            Cancel
          </Button>
          <Button onClick={onNext} data-testid="intake-next-btn"
                  className="rounded-none bg-[var(--st-accent)] hover:bg-[#7dd3fc] text-[#0b1118] font-mono text-xs uppercase tracking-widest h-11 px-6">
            Compute Safety Envelope <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>

      {/* RIGHT: Live preview */}
      <div className="flex flex-col gap-4">
        <Panel testId="preview-hp-panel" raised>
          <PanelHeader label="PREDICTED OUTPUT" sub="LIVE ESTIMATE" />
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="border border-[var(--st-border)] p-3">
              <div className="st-data-label">LOW</div>
              <div className="font-mono text-lg">{predicted ? fmt.hp(predicted.low) : "—"}</div>
            </div>
            <div className="border border-[var(--st-accent)] bg-[var(--st-accent-deep)]/15 p-3">
              <div className="st-data-label text-[var(--st-accent)]">NOMINAL</div>
              <div className="font-mono text-lg text-[var(--st-accent)]">{predicted ? fmt.hp(predicted.nominal) : "—"}</div>
            </div>
            <div className="border border-[var(--st-border)] p-3">
              <div className="st-data-label">HIGH</div>
              <div className="font-mono text-lg">{predicted ? fmt.hp(predicted.high) : "—"}</div>
            </div>
          </div>
          <div className="st-data-label mb-1">TARGET</div>
          <div className="font-mono text-2xl text-[var(--st-text)]">{fmt.hp(intake.target_hp)}</div>
          <div className="text-[11px] text-[var(--st-text-muted)] mt-1 font-mono">
            on {intake.displacement_l}L {intake.cylinders}cyl · {intake.induction} · {intake.fuel_type}
          </div>
        </Panel>

        <Panel testId="preview-ve-panel" raised>
          <PanelHeader label="ESTIMATED VE CURVE" sub="% @ RPM" />
          <div className="h-44 -mx-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={veCurve} margin={{ top: 6, right: 8, left: -10, bottom: 0 }}>
                <XAxis dataKey="rpm" tick={{ fill: "#71717A", fontSize: 9, fontFamily: "JetBrains Mono" }} stroke="#3f3f46" />
                <YAxis tick={{ fill: "#71717A", fontSize: 9, fontFamily: "JetBrains Mono" }} stroke="#3f3f46" domain={[0.3, "auto"]} />
                <RTooltip
                  contentStyle={{ background: "#0e0e10", border: "1px solid #3f3f46", borderRadius: 0, fontFamily: "JetBrains Mono", fontSize: 11 }}
                  labelStyle={{ color: "#a1a1aa" }}
                  formatter={(v) => [`${(v * 100).toFixed(1)}%`, "VE"]}
                />
                <Line type="monotone" dataKey="ve" stroke="#38BDF8" strokeWidth={1.6} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel testId="preview-hints-panel" raised>
          <PanelHeader label="HINT" />
          <div className="flex gap-2 text-xs text-[var(--st-text-secondary)] leading-relaxed">
            <Info className="w-4 h-4 shrink-0 mt-0.5 text-[var(--st-accent)]" />
            <p>
              The starter tune engine biases toward conservative outputs. If your target HP exceeds
              what the safety envelope allows for the chosen hardware, the generator will flag it
              and cap the calibration to safe limits — you can refine in Step 4.
            </p>
          </div>
        </Panel>
      </div>
    </div>
  );
}
