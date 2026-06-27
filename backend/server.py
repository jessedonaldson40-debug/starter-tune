"""
STANDAILONE Starter Tune Engine — FastAPI server
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

import calibration as cal
import diagsim
import inspector

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="StandAIlone Starter Tune Engine")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# MODELS
# ============================================================================

class EngineIntake(BaseModel):
    model_config = ConfigDict(extra="ignore")
    displacement_l: float = Field(..., gt=0, le=12)
    cylinders: int = Field(..., ge=2, le=16)
    induction: str = Field(..., pattern="^(NA|Turbo|Supercharged)$")
    fuel_type: str = Field(..., pattern="^(91|93|98|E85|Methanol|Flex)$")
    target_hp: float = Field(..., gt=0, le=2500)
    rev_limit: int = Field(..., ge=4000, le=11000)
    # Optional
    injector_cc: Optional[float] = 440
    map_sensor_kpa: Optional[int] = None
    compression_ratio: Optional[float] = 10.0
    drivetrain: Optional[str] = None
    transmission: Optional[str] = None
    intended_use: Optional[str] = "street"
    intercooler_class: Optional[str] = "Stock"
    induction_strategy: Optional[str] = "SD"  # MAF or SD
    ethanol_pct: Optional[float] = None
    spool_rpm: Optional[int] = 3000
    turbo_class: Optional[str] = None
    boost_target_pref_kpa: Optional[float] = None
    idle_quality: Optional[str] = "balanced"
    drivability_priority: Optional[str] = "balanced"
    climate: Optional[str] = "temperate"
    hardware_preset: Optional[str] = None


class GenerationAdjustments(BaseModel):
    model_config = ConfigDict(extra="ignore")
    afr_bias: float = 0.0
    timing_bias: float = 0.0
    boost_intent: float = 0.0
    drivability_bias: float = 0.0
    # 4x4 zone grid of additive ignition pull values (negative = pull).
    # zone rows = RPM quartile (low→high), zone cols = load quartile (low→high).
    knock_pull_zones: Optional[list[list[float]]] = None


class GenerateRequest(BaseModel):
    intake: EngineIntake
    adjustments: Optional[GenerationAdjustments] = None


class CreateProfileRequest(BaseModel):
    name: str
    intake: EngineIntake
    tune_package: dict[str, Any]
    adjustments: Optional[GenerationAdjustments] = None
    vehicle_metadata: Optional[dict[str, Any]] = None


class RegenerateRequest(BaseModel):
    intake: EngineIntake
    adjustments: GenerationAdjustments
    note: Optional[str] = None


# ============================================================================
# HELPERS
# ============================================================================

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_mongo(doc: dict[str, Any]) -> dict[str, Any]:
    doc.pop("_id", None)
    return doc


# ============================================================================
# ROUTES — CORE
# ============================================================================

@api_router.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "StandAIlone Starter Tune Engine",
        "version": "1.0.0",
        "status": "online",
    }


@api_router.post("/starter-tune/predict-hp")
async def predict_hp(intake: EngineIntake) -> dict[str, Any]:
    return cal.predict_hp(intake.model_dump())


@api_router.post("/starter-tune/ve-preview")
async def ve_preview(intake: EngineIntake) -> dict[str, Any]:
    data = intake.model_dump()
    curve = cal.estimate_ve_curve(
        displacement_l=data["displacement_l"],
        induction=data["induction"],
        cam_aggressiveness=0.0,
    )
    return {"ve_curve": curve, "rpm_axis": cal.RPM_AXIS}


@api_router.post("/starter-tune/safety-envelope")
async def safety_envelope(intake: EngineIntake) -> dict[str, Any]:
    env = cal.compute_safety_envelope(intake.model_dump())
    return env.to_dict()


@api_router.post("/starter-tune/generate")
async def generate(req: GenerateRequest) -> dict[str, Any]:
    intake = req.intake.model_dump()
    adj = req.adjustments.model_dump() if req.adjustments else None
    package = cal.generate_starter_tune(intake, adj)
    package["generated_at"] = _now_iso()
    package["generation_id"] = str(uuid.uuid4())
    return package


# ============================================================================
# ROUTES — PROFILES
# ============================================================================

@api_router.post("/profiles")
async def create_profile(req: CreateProfileRequest) -> dict[str, Any]:
    profile_id = str(uuid.uuid4())
    now = _now_iso()
    generation_entry = {
        "generation_index": 0,
        "created_at": now,
        "note": "Initial starter tune generation",
        "intake": req.intake.model_dump(),
        "adjustments": (req.adjustments or GenerationAdjustments()).model_dump(),
        "tune_package": req.tune_package,
    }
    profile = {
        "id": profile_id,
        "name": req.name,
        "created_at": now,
        "updated_at": now,
        "vehicle_metadata": req.vehicle_metadata or {},
        "engine_metadata": req.intake.model_dump(),
        "intended_use": req.intake.intended_use,
        "generated_by": "starter-tune-engine",
        "active_generation_index": 0,
        "history": [generation_entry],
        "exports": [],
    }
    await db.profiles.insert_one({**profile})
    return _strip_mongo(profile)


@api_router.get("/profiles")
async def list_profiles() -> list[dict[str, Any]]:
    cur = db.profiles.find({}, {"_id": 0, "history": 0}).sort("created_at", -1)
    return await cur.to_list(500)


@api_router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str) -> dict[str, Any]:
    doc = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Profile not found")
    return doc


@api_router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str) -> dict[str, Any]:
    res = await db.profiles.delete_one({"id": profile_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Profile not found")
    return {"deleted": profile_id}


@api_router.post("/profiles/{profile_id}/regenerate")
async def regenerate_profile(profile_id: str, req: RegenerateRequest) -> dict[str, Any]:
    doc = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Profile not found")

    intake = req.intake.model_dump()
    adj = req.adjustments.model_dump()
    package = cal.generate_starter_tune(intake, adj)

    # Compute diff vs current active generation
    active_idx = doc.get("active_generation_index", 0)
    prev_pkg = doc["history"][active_idx]["tune_package"]
    fuel_diff = cal.compute_map_diff(prev_pkg["fuel_map_ms"], package["fuel_map_ms"])
    ign_diff = cal.compute_map_diff(prev_pkg["ignition_map_deg"], package["ignition_map_deg"])

    new_index = len(doc["history"])
    entry = {
        "generation_index": new_index,
        "created_at": _now_iso(),
        "note": req.note or "Regenerated",
        "intake": intake,
        "adjustments": adj,
        "tune_package": package,
        "diff_vs_previous": {
            "fuel": fuel_diff,
            "ignition": ign_diff,
        },
    }

    await db.profiles.update_one(
        {"id": profile_id},
        {
            "$push": {"history": entry},
            "$set": {
                "active_generation_index": new_index,
                "updated_at": _now_iso(),
            },
        },
    )
    return entry


@api_router.post("/profiles/{profile_id}/revert/{generation_index}")
async def revert_profile(profile_id: str, generation_index: int) -> dict[str, Any]:
    doc = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Profile not found")
    if generation_index < 0 or generation_index >= len(doc["history"]):
        raise HTTPException(400, "Invalid generation index")
    await db.profiles.update_one(
        {"id": profile_id},
        {"$set": {"active_generation_index": generation_index, "updated_at": _now_iso()}},
    )
    return {"profile_id": profile_id, "active_generation_index": generation_index}


@api_router.get("/profiles/{profile_id}/compare/{idx_a}/{idx_b}")
async def compare_generations(profile_id: str, idx_a: int, idx_b: int) -> dict[str, Any]:
    doc = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Profile not found")
    if any(i < 0 or i >= len(doc["history"]) for i in (idx_a, idx_b)):
        raise HTTPException(400, "Invalid index")
    a = doc["history"][idx_a]["tune_package"]
    b = doc["history"][idx_b]["tune_package"]
    return {
        "a_index": idx_a,
        "b_index": idx_b,
        "a_created_at": doc["history"][idx_a]["created_at"],
        "b_created_at": doc["history"][idx_b]["created_at"],
        "fuel_diff": cal.compute_map_diff(a["fuel_map_ms"], b["fuel_map_ms"]),
        "ignition_diff": cal.compute_map_diff(a["ignition_map_deg"], b["ignition_map_deg"]),
        "afr_diff": cal.compute_map_diff(a["afr_target_table"], b["afr_target_table"]),
    }


# ============================================================================
# ROUTES — EXPORTS / HANDOFF
# ============================================================================

EXPORT_TARGETS = {
    "diagsim": {
        "name": "DIAG-SIM",
        "description": "Synthetic OBD/CAN telemetry simulation",
        "format": "diagsim.session.v1",
        "view_route": "/diagsim",
    },
    "inspector": {
        "name": "Tune Inspector Pro",
        "description": "Calibration audit and report package",
        "format": "inspector.report.v2",
        "view_route": "/inspector",
    },
    "forensic": {
        "name": "Forensic Inspector",
        "description": "Compare/audit view for tune deltas",
        "format": "forensic.audit.v1",
        "view_route": "/forensic",
    },
    "ecu": {
        "name": "ECU Flash Artifact",
        "description": "Structured tune package for ECU flashing",
        "format": "ecu.flash.json.v1",
        "view_route": "/ecu",
    },
}


class DiagSimRunRequest(BaseModel):
    scenario: str = "wot_pull"
    seed: Optional[int] = None


@api_router.get("/diagsim/scenarios")
async def diagsim_scenarios() -> dict[str, Any]:
    return diagsim.SCENARIOS


@api_router.post("/profiles/{profile_id}/diagsim/run")
async def diagsim_run(profile_id: str, req: DiagSimRunRequest) -> dict[str, Any]:
    doc = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Profile not found")
    active_idx = doc.get("active_generation_index", 0)
    package = doc["history"][active_idx]["tune_package"]
    intake = doc["engine_metadata"]

    result = diagsim.simulate(package, intake, scenario=req.scenario, seed=req.seed)
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "profile_id": profile_id,
        "profile_name": doc["name"],
        "source_generation_index": active_idx,
        "created_at": _now_iso(),
        "intake_snapshot": intake,
        "envelope_snapshot": package["safety_envelope"],
        **result,
    }
    await db.diagsim_sessions.insert_one({**session})
    return session


@api_router.get("/diagsim/sessions/{session_id}")
async def diagsim_get_session(session_id: str) -> dict[str, Any]:
    doc = await db.diagsim_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Session not found")
    return doc


@api_router.get("/profiles/{profile_id}/diagsim/sessions")
async def diagsim_list_sessions(profile_id: str) -> list[dict[str, Any]]:
    cur = db.diagsim_sessions.find(
        {"profile_id": profile_id},
        {"_id": 0, "samples": 0},
    ).sort("created_at", -1)
    return await cur.to_list(200)


@api_router.post("/profiles/{profile_id}/inspector/audit")
async def inspector_audit(profile_id: str) -> dict[str, Any]:
    doc = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Profile not found")
    active_idx = doc.get("active_generation_index", 0)
    package = doc["history"][active_idx]["tune_package"]
    intake = doc["engine_metadata"]

    report = inspector.audit(package, intake)
    report_id = str(uuid.uuid4())
    saved = {
        "report_id": report_id,
        "profile_id": profile_id,
        "profile_name": doc["name"],
        "source_generation_index": active_idx,
        "created_at": _now_iso(),
        **report,
    }
    await db.inspector_reports.insert_one({**saved})
    return saved


@api_router.get("/inspector/reports/{report_id}")
async def inspector_get_report(report_id: str) -> dict[str, Any]:
    doc = await db.inspector_reports.find_one({"report_id": report_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Report not found")
    return doc


@api_router.get("/profiles/{profile_id}/inspector/reports")
async def inspector_list_reports(profile_id: str) -> list[dict[str, Any]]:
    cur = db.inspector_reports.find(
        {"profile_id": profile_id},
        {"_id": 0, "findings": 0},
    ).sort("created_at", -1)
    return await cur.to_list(200)


@api_router.get("/export/targets")
async def list_export_targets() -> dict[str, Any]:
    return EXPORT_TARGETS


@api_router.post("/profiles/{profile_id}/export/{target}")
async def export_profile(profile_id: str, target: str) -> dict[str, Any]:
    if target not in EXPORT_TARGETS:
        raise HTTPException(400, f"Unknown target: {target}")
    doc = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Profile not found")

    active_idx = doc.get("active_generation_index", 0)
    package = doc["history"][active_idx]["tune_package"]
    intake = doc["engine_metadata"]
    info = EXPORT_TARGETS[target]

    artifact_id = str(uuid.uuid4())
    deep_link: Optional[str] = None
    real_payload: dict[str, Any]

    # Each target invokes the REAL module (no longer a mock dump).
    if target == "diagsim":
        result = diagsim.simulate(package, intake, scenario="wot_pull")
        session_id = str(uuid.uuid4())
        session = {
            "session_id": session_id,
            "profile_id": profile_id,
            "profile_name": doc["name"],
            "source_generation_index": active_idx,
            "created_at": _now_iso(),
            "intake_snapshot": intake,
            "envelope_snapshot": package["safety_envelope"],
            **result,
        }
        await db.diagsim_sessions.insert_one({**session})
        deep_link = f"/diagsim/{session_id}"
        real_payload = {
            "session_id": session_id,
            "scenario": result["scenario"],
            "summary": result["summary"],
            "fault_codes": result["fault_codes"],
        }

    elif target == "inspector":
        report = inspector.audit(package, intake)
        report_id = str(uuid.uuid4())
        saved = {
            "report_id": report_id,
            "profile_id": profile_id,
            "profile_name": doc["name"],
            "source_generation_index": active_idx,
            "created_at": _now_iso(),
            **report,
        }
        await db.inspector_reports.insert_one({**saved})
        deep_link = f"/inspector/{report_id}"
        real_payload = {
            "report_id": report_id,
            "score": report["score"],
            "subsystem_scores": report["subsystem_scores"],
            "counts": report["counts"],
            "top_findings": report["findings"][:5],
        }

    elif target == "forensic":
        history_len = len(doc["history"])
        if history_len < 2:
            # Single generation — produce an audit-against-self artifact
            report = inspector.audit(package, intake)
            real_payload = {
                "mode": "single_generation_audit",
                "score": report["score"],
                "findings_count": len(report["findings"]),
            }
            deep_link = f"/profiles/{profile_id}/compare"
        else:
            a_idx = max(0, active_idx - 1)
            b_idx = active_idx
            a = doc["history"][a_idx]["tune_package"]
            b = doc["history"][b_idx]["tune_package"]
            real_payload = {
                "mode": "two_generation_diff",
                "a_index": a_idx,
                "b_index": b_idx,
                "fuel_diff": cal.compute_map_diff(a["fuel_map_ms"], b["fuel_map_ms"]),
                "ignition_diff": cal.compute_map_diff(a["ignition_map_deg"], b["ignition_map_deg"]),
            }
            deep_link = f"/profiles/{profile_id}/compare"

    else:  # ecu
        real_payload = {
            "format": info["format"],
            "rpm_axis": package["axes"]["rpm"],
            "load_axis": package["axes"]["load_kpa"],
            "fuel_map_ms": package["fuel_map_ms"],
            "ignition_map_deg": package["ignition_map_deg"],
            "afr_target_table": package["afr_target_table"],
            "boost_target_table": package.get("boost_target_table"),
            "idle_table": package["idle_table"],
            "cold_start_table": package["cold_start_table"],
            "safety_envelope": package["safety_envelope"],
            "engine_metadata": intake,
            "checksum_placeholder": artifact_id[:8].upper(),
        }
        deep_link = None  # ECU is a downloadable JSON, no view route

    artifact = {
        "artifact_id": artifact_id,
        "target": target,
        "target_name": info["name"],
        "format": info["format"],
        "generated_at": _now_iso(),
        "profile_id": profile_id,
        "profile_name": doc["name"],
        "source_generation_index": active_idx,
        "engine_metadata": intake,
        "deep_link": deep_link,
        "tune_summary": {
            "fuel_cells": sum(len(r) for r in package["fuel_map_ms"]),
            "ignition_cells": sum(len(r) for r in package["ignition_map_deg"]),
            "confidence_overall": package["confidence"]["overall"],
            "warnings_count": len(package["safety_envelope"]["warnings"]),
            "boost_ceiling_kpa": package["safety_envelope"]["boost_ceiling_kpa"],
        },
        "payload": real_payload,
    }

    log_line = f"[{artifact['generated_at']}] EXPORT {info['name']} :: {artifact_id} :: {doc['name']}"
    await db.profiles.update_one(
        {"id": profile_id},
        {
            "$push": {
                "exports": {
                    "artifact_id": artifact_id,
                    "target": target,
                    "target_name": info["name"],
                    "created_at": _now_iso(),
                    "source_generation_index": active_idx,
                    "deep_link": deep_link,
                    "log_line": log_line,
                }
            }
        },
    )

    return artifact


# ============================================================================
# WIRE UP
# ============================================================================

app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def _shutdown() -> None:
    client.close()
