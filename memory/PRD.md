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

## What's been implemented (initial release + Round 2 + Round 3 + Round 4 polish)

### Round 4 — Final polish (Feb 2026)
- **Testid alignment**: `ExplainFinding` now uses `${testId}-btn` for the button and `${testId}-out` for the output container so selectors like `[data-testid$="-btn"]` and `[data-testid$="-out"]` cleanly differentiate them.
- **AI explanation cache**: in-memory LRU (max 64 entries) keyed by SHA-1 of `finding code + message + remediation + engine_metadata + safety_envelope`. Repeat clicks replay cached tokens in 32-char chunks (~6.6× faster than the live LLM call). Exposed `GET /api/inspector/explain-cache/stats` and `DELETE /api/inspector/explain-cache` for diagnostics/reset. Cache is process-local (acceptable per spec).
- **SSE heartbeat**: live LLM streams emit an `event: ping` frame every 8 tokens for proxy keepalive. Frontend silently ignores unknown event types so no UI changes were needed.

### Round 3 — UX polish + maintainability + AI Explainer
- ExportPanel keeps modal open through sequential exports with SESSION ARTIFACTS list and per-row OPEN/DOWNLOAD actions.
- `/export/{target}` refactored into per-target async helpers dispatched via `EXPORT_HANDLERS`.
- `POST /api/inspector/findings/explain` streams plain-English explanations from Claude Sonnet 4.6 via SSE using Emergent Universal LLM key.

### Backend (`/app/backend/`)
- `calibration.py` — engineering core (VE / fuel / ignition / boost / idle / cold-start / safety envelope / confidence / knock-pull zones)
- `diagsim.py` — real synthetic telemetry simulator (4 scenarios, knock model, OBD-II fault codes)
- `inspector.py` — real rules-based calibration auditor (severity-weighted 0–100 score, subsystem subscores, per-cell findings, prioritized remediation)
- `server.py` — FastAPI routes under `/api`:
  - `/starter-tune/*` — predict / VE / safety envelope / generate (with knock-pull zones)
  - `/profiles/*` CRUD + regenerate + revert + compare
  - `/diagsim/*` — scenarios list + run + session retrieval
  - `/inspector/*` — audit + report retrieval
  - `/export/{target}` — real handoffs to DIAG-SIM, Inspector, Forensic, ECU JSON (with deep_links)
  - `/inspector/findings/explain` — SSE streaming AI explanation (Claude Sonnet 4.6)

### Frontend (`/app/frontend/src/`)
- Industrial design system: Geist + JetBrains Mono, graphite (#141416) + gunmetal panels, sharp 2px corners, amber/red reserved for warnings
- Pages: `Dashboard`, `Wizard` (5 steps with KnockPullEditor in Review), `ProfileDetail` (5 tabs incl. DIAG-SIM sessions + Inspector reports lists), `CompareView`, `DiagSimSession` (telemetry charts), `InspectorReport` (score gauge + findings with AI Explain)
- Components: `Heatmap`, `WizardStepper`, `WarningBanner`, `ConfidenceBadge`, `ExportPanel` (session artifacts list), `KnockPullEditor` (4×4 zone grid), `ExplainFinding` (SSE consumer with AbortController)

### Verified flows (testing agent — Feb 2026)
- **32/32 backend pytest tests pass** across iterations 1+2+3.
- All UI flows verified end-to-end: wizard with knock-pull preset, profile detail tabs, 4 sequential exports in a single modal session, ECU JSON download with correct filename, AI Explainer streaming 920 chars in <15s with RETRY/STOP controls.

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
