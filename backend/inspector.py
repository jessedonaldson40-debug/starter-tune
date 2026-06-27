"""
STANDAILONE Tune Inspector Pro — Rules-Based Calibration Audit
==============================================================
Inspects a generated tune package and produces a structured audit report:
  - per-finding severity + cell coordinates + explanation + remediation
  - aggregate score 0–100
  - subsystem subscores (fuel / ignition / boost / safety)
  - prioritized recommendations

This is a real audit engine, not a placeholder. Findings are derived from
the actual map cells and engine spec.
"""
from __future__ import annotations

from typing import Any


SEVERITY_WEIGHTS = {"critical": 10, "warning": 4, "info": 1}


def _cell_coords(matrix: list[list[float]], predicate) -> list[tuple[int, int]]:
    out = []
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            if predicate(v):
                out.append((r, c))
    return out


def audit(tune_package: dict[str, Any],
           intake: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    fuel_map = tune_package["fuel_map_ms"]
    ign_map = tune_package["ignition_map_deg"]
    afr_table = tune_package["afr_target_table"]
    envelope = tune_package["safety_envelope"]
    rpm_axis = tune_package["axes"]["rpm"]
    load_axis = tune_package["axes"]["load_kpa"]
    boost_table = tune_package.get("boost_target_table")

    # ---- FUEL FINDINGS -----------------------------------------------------
    sub_ms_cells = _cell_coords(fuel_map, lambda v: 0 < v < 0.6)
    if sub_ms_cells:
        findings.append({
            "code": "FUEL_SUB_MS_PW",
            "severity": "warning",
            "subsystem": "fuel",
            "message": f"{len(sub_ms_cells)} cells request pulse width under 0.6 ms. Injectors are non-linear in this range and may dribble.",
            "cells": sub_ms_cells[:24],
            "remediation": "Consider raising idle/low-load AFR target, smaller injectors, or staged injection.",
        })

    long_pw_cells = _cell_coords(fuel_map, lambda v: v > 18.0)
    if long_pw_cells:
        findings.append({
            "code": "FUEL_PW_NEAR_DUTY_CAP",
            "severity": "critical" if any(v > 22 for row in fuel_map for v in row) else "warning",
            "subsystem": "fuel",
            "message": f"{len(long_pw_cells)} cells exceed 18 ms pulse width — approaching or above 85% injector duty at high RPM.",
            "cells": long_pw_cells[:24],
            "remediation": "Upgrade to larger injectors or reduce target HP / boost ceiling.",
        })

    # ---- IGNITION FINDINGS -------------------------------------------------
    ceiling = envelope["ignition_ceiling"]
    over_ceiling = _cell_coords(ign_map, lambda v: v > ceiling + 0.1)
    if over_ceiling:
        findings.append({
            "code": "IGN_OVER_ENVELOPE",
            "severity": "critical",
            "subsystem": "ignition",
            "message": f"{len(over_ceiling)} ignition cells above safety ceiling of {ceiling}°.",
            "cells": over_ceiling[:24],
            "remediation": "This should never happen for a starter tune. Recompute envelope.",
        })

    very_low_timing = _cell_coords(ign_map, lambda v: v < 4.0)
    if len(very_low_timing) > 6:
        findings.append({
            "code": "IGN_AGGRESSIVE_KNOCK_PULL",
            "severity": "info",
            "subsystem": "ignition",
            "message": f"{len(very_low_timing)} cells pulled below 4° BTDC. Heavy knock-pull region detected.",
            "cells": very_low_timing[:24],
            "remediation": "If this is intentional, validate on dyno. If not, consider lower boost target or higher octane.",
        })

    # ---- AFR FINDINGS ------------------------------------------------------
    afr_min = envelope["afr_min"]
    afr_max = envelope["afr_max"]
    rich_cells = _cell_coords(afr_table, lambda v: v < afr_min - 0.05)
    lean_cells = _cell_coords(afr_table, lambda v: v > afr_max + 0.05)
    if rich_cells:
        findings.append({
            "code": "AFR_BELOW_FLOOR",
            "severity": "warning",
            "subsystem": "fuel",
            "message": f"{len(rich_cells)} AFR target cells below floor {afr_min}.",
            "cells": rich_cells[:24],
            "remediation": "Excessive enrichment can foul plugs and reduce power.",
        })
    if lean_cells:
        findings.append({
            "code": "AFR_ABOVE_CEILING",
            "severity": "critical",
            "subsystem": "fuel",
            "message": f"{len(lean_cells)} AFR target cells above ceiling {afr_max}.",
            "cells": lean_cells[:24],
            "remediation": "Lean targets at load are dangerous — risk of lean-knock.",
        })

    # ---- BOOST FINDINGS ----------------------------------------------------
    if boost_table:
        max_boost = max(b["boost_kpa"] for b in boost_table)
        ceiling_kpa = envelope.get("boost_ceiling_kpa") or 0
        if max_boost > ceiling_kpa + 0.1:
            findings.append({
                "code": "BOOST_OVER_ENVELOPE",
                "severity": "critical",
                "subsystem": "boost",
                "message": f"Peak boost {max_boost} kPa exceeds envelope ceiling {ceiling_kpa} kPa.",
                "remediation": "Reduce boost intent or upgrade intercooler / fuel system.",
            })
        if ceiling_kpa and max_boost < ceiling_kpa * 0.55:
            findings.append({
                "code": "BOOST_UNDERUTILIZED",
                "severity": "info",
                "subsystem": "boost",
                "message": f"Peak boost target is {max_boost:.0f} kPa, well below available ceiling of {ceiling_kpa} kPa.",
                "remediation": "Headroom exists for higher boost if hardware supports it.",
            })

    # ---- ENVELOPE WARNINGS RE-ELEVATED ------------------------------------
    for w in envelope.get("warnings", []):
        findings.append({
            "code": w["code"],
            "severity": "critical" if w["level"] == "danger" else w["level"],
            "subsystem": "safety",
            "message": w["message"],
            "remediation": "Verify hardware spec before flashing or running the vehicle.",
        })

    # ---- HARDWARE COMPLETENESS ---------------------------------------------
    if not intake.get("compression_ratio"):
        findings.append({
            "code": "META_NO_COMPRESSION",
            "severity": "info",
            "subsystem": "safety",
            "message": "Compression ratio not provided; ignition model used default 10:1.",
            "remediation": "Provide actual CR for tighter knock model.",
        })
    if not intake.get("injector_cc"):
        findings.append({
            "code": "META_NO_INJECTOR",
            "severity": "info",
            "subsystem": "fuel",
            "message": "Injector flow not provided; fuel mass calculation used default 440cc.",
            "remediation": "Provide actual injector flow for accurate pulse width.",
        })

    # ---- SCORING -----------------------------------------------------------
    penalty = sum(SEVERITY_WEIGHTS.get(f["severity"], 0) for f in findings)
    score = max(0, 100 - penalty)
    counts = {
        "critical": sum(1 for f in findings if f["severity"] == "critical"),
        "warning": sum(1 for f in findings if f["severity"] == "warning"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
    }
    sub_scores = {}
    for sub in ("fuel", "ignition", "boost", "safety"):
        sub_pen = sum(SEVERITY_WEIGHTS.get(f["severity"], 0) for f in findings if f["subsystem"] == sub)
        sub_scores[sub] = max(0, 100 - sub_pen)

    # ---- RECOMMENDATIONS (prioritized) ------------------------------------
    crit = [f for f in findings if f["severity"] == "critical"][:3]
    warn = [f for f in findings if f["severity"] == "warning"][:3]
    recommendations = [f["remediation"] for f in crit + warn]
    if not recommendations:
        recommendations = [
            "No critical issues detected. Validate on dyno before street use.",
            "Log AFR + knock under realistic load before raising any aggressiveness sliders.",
        ]

    return {
        "score": score,
        "subsystem_scores": sub_scores,
        "counts": counts,
        "findings": findings,
        "recommendations": recommendations,
        "axes": {"rpm": rpm_axis, "load_kpa": load_axis},
        "tune_summary": {
            "fuel_cells": sum(len(r) for r in fuel_map),
            "ignition_cells": sum(len(r) for r in ign_map),
            "ignition_ceiling": ceiling,
            "boost_ceiling_kpa": envelope.get("boost_ceiling_kpa"),
            "predicted_hp": tune_package.get("predicted_hp"),
        },
    }
