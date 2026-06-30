"""
STANDAILONE Calibration Package (SACP) — Schema v1.0.0
======================================================

This module defines the canonical, versioned calibration package that every
application in the StandAIlone ecosystem reads and writes. The package is the
single source of truth: no application should ever exchange screenshots, CSVs
or page state — only this object.

Suggested file extensions: .sacp or .standalone (JSON-serializable in v1).

Sections (top-level keys):

  package_metadata          ID, schema version, timestamps, status, checksum
  vehicle                   Vehicle / chassis metadata
  engine                    Engine specifications
  hardware                  Installed hardware package
  calibration               All calibration tables with per-table metadata
  safety_envelope           Bounds + risk indicators
  telemetry_assumptions     Expected operating behaviour (DIAG-SIM baseline)
  generation_metadata       Algorithm version, presets, assumptions, overrides
  confidence                Per-subsystem + overall scores
  warnings                  Active warning entries
  simulation                Reserved for DIAG-SIM input
  inspector                 Reserved for Tune Inspector Pro output
  compare_history           Revision log for undo / compare
  exports                   Every export artifact (target, time, checksum)
  notes                     Free-form engineering notes

The schema is built around `pydantic` models with `extra='ignore'` for forward
compatibility — future minor revisions can add fields without breaking older
readers. A `migrate()` placeholder is reserved for schema-version upgrades.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


SACP_SCHEMA_VERSION = "1.0.0"
SACP_GENERATOR = "starter-tune-engine"
SACP_FILE_EXTENSION = ".sacp"


# ===========================================================================
# Helper types
# ===========================================================================

class _SacpModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class TableMetadata(_SacpModel):
    """Per-table metadata carried alongside every calibration table."""
    name: str
    rows: int = 0
    cols: int = 0
    axis_rows: str = ""           # human-readable e.g. "MAP kPa"
    axis_cols: str = ""           # e.g. "RPM"
    units: str = ""
    interpolation: str = "bilinear"
    confidence: float = 0.0
    notes: Optional[str] = None


class Table2D(_SacpModel):
    """Standard 2D calibration table."""
    values: list[list[float]]
    axis_rpm: list[int] = []
    axis_load_kpa: list[int] = []
    metadata: TableMetadata


class Table1D(_SacpModel):
    """1D table — used for cold-start / idle / VE curve etc."""
    values: list[float]
    axis: list[float] = []
    axis_label: str = ""
    metadata: TableMetadata


# ===========================================================================
# Top-level sections
# ===========================================================================

class PackageMetadata(_SacpModel):
    package_id: str
    schema_version: str = SACP_SCHEMA_VERSION
    application_version: str = "1.0.0"
    created_at: str
    last_modified_at: str
    created_by: str = "starter-tune-engine"
    last_modified_by: str = "starter-tune-engine"
    origin_application: str = "Starter Tune Engine"
    generator_version: str = SACP_GENERATOR
    checksum: Optional[str] = None
    status: str = "Generated"   # Draft / Generated / Simulated / Validated / Exported
    name: str = ""
    extensions: list[str] = [".sacp", ".standalone"]


class Vehicle(_SacpModel):
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    market: Optional[str] = None
    vin: Optional[str] = None
    platform: Optional[str] = None
    drivetrain: Optional[str] = None
    transmission: Optional[str] = None
    vehicle_weight_kg: Optional[float] = None
    wheel_diameter_in: Optional[float] = None
    gear_ratios: Optional[list[float]] = None
    final_drive: Optional[float] = None


class TurboMetadata(_SacpModel):
    class_label: Optional[str] = None      # e.g. "Medium frame (~64mm)"
    a_r: Optional[float] = None
    spool_rpm: Optional[int] = None
    wastegate_type: Optional[str] = None


class Engine(_SacpModel):
    displacement_l: float
    cylinder_count: int
    cylinder_config: Optional[str] = None  # I4, V6, V8, H4, etc.
    compression_ratio: Optional[float] = None
    fuel_type: str
    induction_type: str
    turbo: Optional[TurboMetadata] = None
    rev_limit: int
    map_sensor_kpa: Optional[int] = None
    maf_strategy: Optional[str] = None     # MAF / SD / Alpha-N
    throttle_type: Optional[str] = None
    injector_size_cc: Optional[float] = None
    injector_count: Optional[int] = None
    fuel_pressure_bar: Optional[float] = None
    camshaft_profile: Optional[str] = None
    valvetrain: Optional[str] = None
    ethanol_pct: Optional[float] = None


class HardwarePackage(_SacpModel):
    turbo: Optional[str] = None
    wastegate: Optional[str] = None
    intercooler: Optional[str] = None
    intercooler_class: Optional[str] = None
    fuel_pump: Optional[str] = None
    injectors: Optional[str] = None
    wideband: Optional[str] = None
    map_sensor: Optional[str] = None
    maf_sensor: Optional[str] = None
    ecu: Optional[str] = None
    boost_control_solenoid: Optional[str] = None
    exhaust: Optional[str] = None
    intake: Optional[str] = None
    cooling_package: Optional[str] = None


class Calibration(_SacpModel):
    """All calibration tables. Each carries its own metadata + confidence."""
    fuel_table: Optional[Table2D] = None
    ignition_table: Optional[Table2D] = None
    afr_target_table: Optional[Table2D] = None
    boost_target_table: Optional[list[dict[str, float]]] = None   # rpm/kpa pairs
    idle_tables: Optional[dict[str, Any]] = None
    cold_start_tables: Optional[dict[str, Any]] = None
    warmup_enrichment: Optional[dict[str, Any]] = None
    acceleration_enrichment: Optional[dict[str, Any]] = None
    torque_limits: Optional[dict[str, Any]] = None
    load_limits: Optional[dict[str, Any]] = None
    rev_limiter: Optional[dict[str, Any]] = None
    ve_curve: Optional[Table1D] = None
    supporting_tables: dict[str, Any] = {}


class SafetyEnvelope(_SacpModel):
    max_ignition_deg: Optional[float] = None
    min_afr: Optional[float] = None
    max_afr: Optional[float] = None
    max_boost_kpa: Optional[float] = None
    max_injector_duty_pct: float = 85.0
    max_estimated_torque_nm: Optional[float] = None
    thermal_risk: Optional[str] = None
    knock_risk: Optional[str] = None
    fuel_system_margin_pct: Optional[float] = None
    turbo_margin: Optional[str] = None
    overall_safety_confidence: float = 0.0
    warnings: list[dict[str, Any]] = []


class TelemetryAssumptions(_SacpModel):
    expected_idle_rpm: Optional[int] = None
    expected_cruise_afr: Optional[float] = None
    expected_boost_curve: Optional[list[dict[str, float]]] = None
    expected_injector_duty_pct: Optional[float] = None
    expected_knock_activity: str = "low"
    expected_ve_curve: Optional[list[dict[str, float]]] = None
    expected_fuel_pressure_bar: Optional[float] = None
    expected_iat_range_c: list[float] = [20.0, 65.0]
    expected_coolant_range_c: list[float] = [85.0, 105.0]
    expected_lambda_range: list[float] = [0.75, 1.05]


class GenerationMetadata(_SacpModel):
    generation_algorithm: str = "starter-tune-engine"
    preset_used: Optional[str] = None
    starter_tune_version: str = "1.0.0"
    hardware_assumptions: list[str] = []
    confidence: float = 0.0
    known_limitations: list[str] = []
    safety_warnings: list[dict[str, Any]] = []
    user_overrides: dict[str, Any] = {}
    adjustments_applied: dict[str, Any] = {}


class ConfidenceScores(_SacpModel):
    fuel: float = 0.0
    ignition: float = 0.0
    boost: float = 0.0
    idle: float = 0.0
    cold_start: float = 0.0
    hardware_match: float = 0.0
    overall: float = 0.0


class SimulationSection(_SacpModel):
    """Reserved for DIAG-SIM. Empty by default — schema only."""
    preset: Optional[str] = "wot_pull"
    scenario: Optional[str] = None
    weather: Optional[str] = "temperate"
    elevation_m: float = 0.0
    fuel_quality: Optional[str] = None
    driver_style: Optional[str] = "balanced"
    target_duration_s: Optional[float] = None
    last_sessions: list[dict[str, Any]] = []   # references only — full session lives in db.diagsim_sessions


class InspectorSection(_SacpModel):
    """Reserved for Tune Inspector Pro. Empty by default."""
    evidence: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []
    correlation: dict[str, Any] = {}
    inspector_version: Optional[str] = None
    last_reports: list[dict[str, Any]] = []    # references only


class CompareRevision(_SacpModel):
    revision_index: int
    timestamp: str
    changed_tables: list[str] = []
    changed_cells: dict[str, int] = {}  # table_name -> changed count
    reason: str = ""
    user: str = "system"
    confidence_delta: float = 0.0
    safety_delta: float = 0.0
    snapshot: Optional[dict[str, Any]] = None  # full calibration snapshot


class ExportRecord(_SacpModel):
    target_ecu: Optional[str] = None
    target_application: Optional[str] = None
    definition_pack: Optional[str] = None
    export_time: str
    export_version: str = "1.0.0"
    export_status: str = "success"
    checksum: Optional[str] = None
    artifact_id: Optional[str] = None
    deep_link: Optional[str] = None


class Note(_SacpModel):
    note_id: str
    created_at: str
    author: str = "system"
    text: str
    section_anchor: Optional[str] = None     # optional anchor to a section


# ===========================================================================
# Root package
# ===========================================================================

class SacpPackage(_SacpModel):
    package_metadata: PackageMetadata
    vehicle: Vehicle = Vehicle()
    engine: Engine
    hardware: HardwarePackage = HardwarePackage()
    calibration: Calibration = Calibration()
    safety_envelope: SafetyEnvelope = SafetyEnvelope()
    telemetry_assumptions: TelemetryAssumptions = TelemetryAssumptions()
    generation_metadata: GenerationMetadata = GenerationMetadata()
    confidence: ConfidenceScores = ConfidenceScores()
    warnings: list[dict[str, Any]] = []
    simulation: SimulationSection = SimulationSection()
    inspector: InspectorSection = InspectorSection()
    compare_history: list[CompareRevision] = []
    exports: list[ExportRecord] = []
    notes: list[Note] = []


# ===========================================================================
# Helpers
# ===========================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_checksum(payload: dict[str, Any]) -> str:
    """Stable SHA-256 of the package excluding checksum / timestamps."""
    body = json.loads(json.dumps(payload, default=str, sort_keys=True))
    meta = body.get("package_metadata", {}) or {}
    meta.pop("checksum", None)
    meta.pop("last_modified_at", None)
    meta.pop("created_at", None)
    body["package_metadata"] = meta
    blob = json.dumps(body, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def stamp_checksum(pkg: dict[str, Any]) -> dict[str, Any]:
    pkg.setdefault("package_metadata", {})
    pkg["package_metadata"]["checksum"] = compute_checksum(pkg)
    return pkg


def validate(payload: dict[str, Any]) -> SacpPackage:
    """Parse + validate a package dict. Raises pydantic.ValidationError on failure."""
    return SacpPackage.model_validate(payload)


def migrate(payload: dict[str, Any], target_version: str = SACP_SCHEMA_VERSION) -> dict[str, Any]:
    """Forward-migrate older packages. Placeholder — only 1.0.0 exists today."""
    incoming = (payload.get("package_metadata") or {}).get("schema_version", "1.0.0")
    if incoming == target_version:
        return payload
    # Future: chain migrations 1.0.0 -> 1.1.0 -> 2.0.0 etc.
    raise ValueError(f"Unsupported schema version {incoming!r}; only {target_version} is known.")


# ===========================================================================
# Construction from existing profile/tune records
# ===========================================================================

def _table_meta(name: str, rows: int, cols: int,
                 axis_rows: str, axis_cols: str, units: str,
                 confidence: float, notes: Optional[str] = None) -> TableMetadata:
    return TableMetadata(
        name=name, rows=rows, cols=cols,
        axis_rows=axis_rows, axis_cols=axis_cols, units=units,
        interpolation="bilinear", confidence=confidence, notes=notes,
    )


def _calibration_from_tune(tune: dict[str, Any], conf: dict[str, float]) -> Calibration:
    rpm_axis = (tune.get("axes") or {}).get("rpm", [])
    load_axis = (tune.get("axes") or {}).get("load_kpa", [])

    def mk_2d(name, values, units, conf_v, notes=None):
        if not values:
            return None
        return Table2D(
            values=values,
            axis_rpm=rpm_axis,
            axis_load_kpa=load_axis,
            metadata=_table_meta(name, len(values), len(values[0]) if values else 0,
                                  "MAP kPa", "RPM", units, conf_v, notes),
        )

    return Calibration(
        fuel_table=mk_2d("Fuel Pulse Width", tune.get("fuel_map_ms"), "ms",
                         conf.get("fuel", 0.0), "Injector pulse width"),
        ignition_table=mk_2d("Ignition Advance", tune.get("ignition_map_deg"), "deg BTDC",
                             conf.get("ignition", 0.0), "Envelope-clamped"),
        afr_target_table=mk_2d("AFR Target", tune.get("afr_target_table"), "AFR",
                                conf.get("fuel", 0.0), "Stoich-anchored target"),
        boost_target_table=tune.get("boost_target_table"),
        idle_tables=tune.get("idle_table"),
        cold_start_tables=tune.get("cold_start_table"),
        ve_curve=Table1D(
            values=[c.get("ve", 0.0) for c in (tune.get("ve_curve") or [])],
            axis=[c.get("rpm", 0) for c in (tune.get("ve_curve") or [])],
            axis_label="RPM",
            metadata=_table_meta("Volumetric Efficiency", len(tune.get("ve_curve") or []),
                                  1, "VE", "RPM", "ratio", conf.get("fuel", 0.0)),
        ) if tune.get("ve_curve") else None,
        rev_limiter={"rpm": (tune.get("axes") or {}).get("rpm", [None])[-1]},
        supporting_tables={},
    )


def _safety_envelope_from_tune(tune: dict[str, Any]) -> SafetyEnvelope:
    env = tune.get("safety_envelope") or {}
    return SafetyEnvelope(
        max_ignition_deg=env.get("ignition_ceiling"),
        min_afr=env.get("afr_min"),
        max_afr=env.get("afr_max"),
        max_boost_kpa=env.get("boost_ceiling_kpa"),
        max_estimated_torque_nm=env.get("torque_baseline_nm"),
        thermal_risk=env.get("thermal_risk"),
        knock_risk=env.get("knock_sensitivity"),
        fuel_system_margin_pct=env.get("injector_headroom_pct"),
        turbo_margin=None,
        overall_safety_confidence=env.get("confidence", 0.0),
        warnings=env.get("warnings", []),
    )


def _telemetry_assumptions_from_tune(tune: dict[str, Any], engine_meta: dict[str, Any]) -> TelemetryAssumptions:
    boost = tune.get("boost_target_table")
    return TelemetryAssumptions(
        expected_idle_rpm=850,
        expected_cruise_afr=14.4,
        expected_boost_curve=boost,
        expected_injector_duty_pct=85.0 - (tune.get("safety_envelope", {}).get("injector_headroom_pct") or 0),
        expected_knock_activity=tune.get("safety_envelope", {}).get("knock_sensitivity", "low"),
        expected_ve_curve=tune.get("ve_curve"),
        expected_fuel_pressure_bar=engine_meta.get("fuel_pressure_bar", 3.0),
    )


def _engine_from_intake(intake: dict[str, Any]) -> Engine:
    turbo = None
    if intake.get("induction") in ("Turbo", "Supercharged"):
        turbo = TurboMetadata(
            class_label=intake.get("turbo_class"),
            spool_rpm=intake.get("spool_rpm"),
        )
    return Engine(
        displacement_l=float(intake.get("displacement_l", 0)),
        cylinder_count=int(intake.get("cylinders", 0)),
        cylinder_config=None,
        compression_ratio=intake.get("compression_ratio"),
        fuel_type=intake.get("fuel_type", "93"),
        induction_type=intake.get("induction", "NA"),
        turbo=turbo,
        rev_limit=int(intake.get("rev_limit", 6800)),
        map_sensor_kpa=intake.get("map_sensor_kpa"),
        maf_strategy=intake.get("induction_strategy", "SD"),
        injector_size_cc=intake.get("injector_cc"),
        injector_count=int(intake.get("cylinders", 0)),
        ethanol_pct=intake.get("ethanol_pct"),
    )


def from_profile(profile_doc: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a stored profile document (existing legacy shape) into a full SACP
    dict ready to be returned, serialized to .sacp, or persisted in db.packages.

    The profile shape is:
      {
        id, name, created_at, updated_at, engine_metadata, intended_use,
        active_generation_index, history[{generation_index, created_at, note,
          intake, adjustments, tune_package, diff_vs_previous?}],
        exports[], vehicle_metadata
      }
    """
    history = profile_doc.get("history") or []
    active_idx = profile_doc.get("active_generation_index", 0)
    active_entry = history[active_idx] if history else {}
    tune = active_entry.get("tune_package") or {}
    intake = profile_doc.get("engine_metadata") or {}
    conf = tune.get("confidence") or {}
    vehicle_meta = profile_doc.get("vehicle_metadata") or {}

    pkg_meta = PackageMetadata(
        package_id=profile_doc.get("id", str(uuid.uuid4())),
        created_at=profile_doc.get("created_at", _now_iso()),
        last_modified_at=profile_doc.get("updated_at", _now_iso()),
        name=profile_doc.get("name", "Untitled"),
        status="Generated",
    )

    vehicle = Vehicle(
        drivetrain=vehicle_meta.get("drivetrain") or intake.get("drivetrain"),
        transmission=vehicle_meta.get("transmission") or intake.get("transmission"),
    )

    engine = _engine_from_intake(intake)
    hardware = HardwarePackage(intercooler_class=intake.get("intercooler_class"))
    calibration = _calibration_from_tune(tune, conf)
    safety = _safety_envelope_from_tune(tune)
    telemetry = _telemetry_assumptions_from_tune(tune, intake)

    confidence = ConfidenceScores(
        fuel=conf.get("fuel", 0.0),
        ignition=conf.get("ignition", 0.0),
        boost=conf.get("boost", 0.0),
        idle=conf.get("idle", 0.0),
        cold_start=conf.get("idle", 0.0),
        hardware_match=conf.get("overall", 0.0),
        overall=conf.get("overall", 0.0),
    )

    gen_meta = GenerationMetadata(
        generation_algorithm=tune.get("algorithm_version", "starter-tune-engine/1.0"),
        preset_used=intake.get("hardware_preset"),
        starter_tune_version="1.0.0",
        hardware_assumptions=tune.get("assumptions", []),
        confidence=conf.get("overall", 0.0),
        safety_warnings=safety.warnings,
        adjustments_applied=tune.get("adjustments_applied", {}),
        user_overrides={},
    )

    revisions: list[CompareRevision] = []
    for idx, entry in enumerate(history):
        diff = entry.get("diff_vs_previous") or {}
        revisions.append(CompareRevision(
            revision_index=idx,
            timestamp=entry.get("created_at", _now_iso()),
            changed_tables=[k for k in ("fuel", "ignition") if (diff.get(k) or {}).get("changed_count", 0) > 0],
            changed_cells={k: (diff.get(k) or {}).get("changed_count", 0) for k in ("fuel", "ignition")},
            reason=entry.get("note", ""),
            user="system",
            confidence_delta=0.0,
            safety_delta=0.0,
            snapshot=None,
        ))

    exports = [
        ExportRecord(
            target_ecu=None,
            target_application=e.get("target_name"),
            export_time=e.get("created_at", _now_iso()),
            export_version="1.0.0",
            export_status="success",
            artifact_id=e.get("artifact_id"),
            deep_link=e.get("deep_link"),
        )
        for e in (profile_doc.get("exports") or [])
    ]

    notes_raw = profile_doc.get("notes") or []
    notes = [Note(**n) if isinstance(n, dict) else Note(note_id=str(uuid.uuid4()),
                                                          created_at=_now_iso(),
                                                          author="system",
                                                          text=str(n))
             for n in notes_raw]

    pkg = SacpPackage(
        package_metadata=pkg_meta,
        vehicle=vehicle,
        engine=engine,
        hardware=hardware,
        calibration=calibration,
        safety_envelope=safety,
        telemetry_assumptions=telemetry,
        generation_metadata=gen_meta,
        confidence=confidence,
        warnings=safety.warnings,
        simulation=SimulationSection(scenario="wot_pull"),
        inspector=InspectorSection(),
        compare_history=revisions,
        exports=exports,
        notes=notes,
    ).model_dump()

    return stamp_checksum(pkg)


def section_summary() -> dict[str, Any]:
    """Schema introspection for the frontend."""
    return {
        "schema_version": SACP_SCHEMA_VERSION,
        "file_extensions": [".sacp", ".standalone"],
        "sections": [
            {"key": "package_metadata", "required": True, "description": "ID, schema version, timestamps, checksum"},
            {"key": "vehicle", "required": False, "description": "Vehicle / chassis metadata"},
            {"key": "engine", "required": True, "description": "Engine specifications"},
            {"key": "hardware", "required": False, "description": "Installed hardware package"},
            {"key": "calibration", "required": True, "description": "All calibration tables"},
            {"key": "safety_envelope", "required": True, "description": "Bounds + risk indicators"},
            {"key": "telemetry_assumptions", "required": False, "description": "DIAG-SIM baseline"},
            {"key": "generation_metadata", "required": True, "description": "Algorithm version + presets + assumptions"},
            {"key": "confidence", "required": True, "description": "Per-subsystem + overall scores"},
            {"key": "warnings", "required": False, "description": "Active warning entries"},
            {"key": "simulation", "required": False, "description": "Reserved for DIAG-SIM input"},
            {"key": "inspector", "required": False, "description": "Reserved for Tune Inspector Pro"},
            {"key": "compare_history", "required": False, "description": "Revision log"},
            {"key": "exports", "required": False, "description": "Export artifacts"},
            {"key": "notes", "required": False, "description": "Free-form notes"},
        ],
    }
