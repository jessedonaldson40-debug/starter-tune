# STANDAILONE Starter Tune Engine — PRD

## Problem statement (original)
Build a production-grade full-stack web application module called STANDAILONE STARTER TUNE ENGINE — a serious calibration-generation system inside the StandAIlone ecosystem. Its purpose is to eliminate the 30–60 minute setup barrier for new users by generating a complete starter calibration from minimal engine metadata. The system must produce a credible, conservative, professional base tune package including fuel, ignition, and safety envelope outputs, then hand that tune into the rest of the StandAIlone ecosystem.

## User choices (gathered Feb 2026)
- Full end-to-end workflow (intake → safety envelope → map gen → review/adjust → save → export hooks) with mock handoffs to DIAG-SIM / Tune Inspector Pro / Forensic Inspector
- Deterministic engineering formulas (no LLM) — VE-based fuel mass, MBT-anchored ignition, knock-margin clamping
- No auth — single-tenant module, profiles stored in MongoDB
- ECU export = structured JSON artifact
- 2D heatmaps only (no 3D)

## User personas
- **Beginner tuner / first-time user**: needs to go from "I just bought hardware" to "I have a credible starter calibration" without 30+ minutes of manual table entry.
- **Experienced tuner**: wants a fast, conservative baseline they can refine with sliders, compare/undo, and export to DIAG-SIM or Tune Inspector Pro.
- **Engineer / auditor**: needs forensic compare view of generation history with deltas.

## Core requirements (static)
- Conservative-by-default calibration
- Full safety envelope as a hard limiter on generated maps
- Profile persistence with full undo / compare history
- Handoff to DIAG-SIM / Tune Inspector Pro / Forensic Inspector / ECU
- Industrial / engineering UI (graphite + gunmetal, sharp corners, monospace technical readouts)

## What's been implemented (2026-02 initial release)

### Backend (`/app/backend/`)
- `calibration.py` — engineering core:
  - VE curve estimator (parabolic torque-peak shifted by induction)
  - AFR target table generator (stoich-anchored, fuel-aware, boost-aware enrichment)
  - Fuel map (16x16 injector pulse width, ms) from VE × air-mass × AFR × injector flow
  - Ignition map (16x16, deg BTDC) — MBT model with octane / CR / load / boost trim, hard-clamped by envelope ceiling
  - Boost target curve respecting spool RPM, envelope ceiling, taper at top
  - Idle and cold-start tables vs coolant temp
  - Safety envelope (AFR floor/ceiling, ignition ceiling, boost ceiling, torque baseline, knock & thermal risk, injector headroom @ 85% duty, warnings, confidence)
  - Per-subsystem and overall confidence scoring
  - Map diff with changed-cell count and max delta
- `server.py` — FastAPI routes under `/api`:
  - `/starter-tune/predict-hp`, `/ve-preview`, `/safety-envelope`, `/generate`
  - `/profiles` CRUD + `/regenerate` + `/revert/{idx}` + `/compare/{a}/{b}`
  - `/export/targets`, `/profiles/{id}/export/{diagsim|inspector|forensic|ecu}`

### Frontend (`/app/frontend/src/`)
- Industrial design system bound to shadcn dark tokens — Geist + JetBrains Mono, graphite (#141416) + gunmetal panels (#1A1A1D), steel borders, sharp 2px corners, amber/red reserved for warnings.
- Pages:
  - `Dashboard` — hero CTA, engine-coverage stats, profile cards
  - `Wizard` — 5-step flow with persistent stepper (Intake → Safety → Generate → Review → Save)
  - `ProfileDetail` — tabs for Tune Maps / Supporting Tables / Safety Envelope / Generation History / Export Log
  - `CompareView` — Forensic compare with diff heatmaps and side-by-side panels
- Components: `Heatmap` (Viridis fuel / Diverging ignition / Diverging delta), `WizardStepper`, `WarningBanner`, `ConfidenceBadge`, `ExportPanel`, `PanelHeader`
- Live VE curve + HP prediction in Step 1, debounced slider regeneration in Step 4, changed-cell highlighting + diff overlay

### Verified flows (testing agent — Feb 2026)
- 13/13 backend pytest API tests pass
- Full Playwright wizard run: Dashboard → Intake (preset auto-fill) → Safety → Generate → Review (slider regen + change indicator) → Save → ProfileDetail (all tabs) → Export Panel (all 4 handoffs) → Forensic Compare
- Aggressive target correctly flagged with `AGGRESSIVE_TARGET` and `THERMAL_HIGH` warnings; ignition map clamped to envelope ceiling

## Prioritized backlog

### P0 (none — initial release shipped)
_All P0 features delivered._

### P1
- Replace mock DIAG-SIM / Tune Inspector / Forensic exports with real ecosystem handoffs once those modules exist.
- Persist regeneration adjustments per-axis history so deltas show "what changed and why" automatically.
- Add knock-pull table editing in the review step (currently auto-clamped only).
- Auth + multi-tenant profile ownership (deferred per user choice).
- 3D surface visualization toggle for fuel / ignition (deferred per user choice).

### P2
- AI-assisted calibration recommendations (LLM-suggested adjustments respecting envelope).
- Auto-retune workflow that consumes telemetry and proposes deltas.
- Real ECU-vendor flash format adapters (Cobb, Hondata, OpenECU, MoTeC, etc.).
- Forensic compare against later uploaded *tuned* version (cross-source compare).

## Next tasks
1. Wire real DIAG-SIM / Tune Inspector Pro / Forensic Inspector handoffs when those modules come online.
2. Add knock-pull table editor in Review step.
3. Optional: replace deprecated FastAPI `on_event("shutdown")` with lifespan handlers.
