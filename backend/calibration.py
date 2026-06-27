"""
STANDAILONE Starter Tune Engine — Calibration Core
===================================================
Deterministic, conservative engineering-grade calibration generator.

This module produces:
- Volumetric Efficiency (VE) curve estimate
- Fuel map (injector pulse width, ms) over RPM x MAP
- Ignition map (degrees BTDC) over RPM x MAP
- Boost target table (turbo / supercharged)
- AFR target table
- Idle / cold start baseline tables
- Safety envelope (AFR / ignition / boost / torque / risk)
- Per-subsystem and overall confidence scoring

Conservative by design: every output is biased toward safety margin first.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# ============================================================================
# AXES
# ============================================================================

RPM_AXIS = [800, 1200, 1600, 2000, 2400, 2800, 3200, 3600,
            4000, 4400, 4800, 5200, 5600, 6000, 6400, 6800]

# Load axis is dynamic — 100 kPa max for NA, up to ~260 kPa for boosted
NA_LOAD_AXIS = [20, 28, 36, 44, 52, 60, 68, 76, 82, 86, 90, 93, 96, 98, 100, 102]
BOOST_LOAD_AXIS = [20, 35, 50, 65, 80, 95, 110, 125, 140, 160, 180, 200, 220, 240, 255, 270]

IDLE_RPM_AXIS = [600, 750, 900, 1050, 1200, 1400, 1600, 1800]
CLT_AXIS = [-20, -10, 0, 20, 40, 60, 80, 95]  # coolant temperature C

# ============================================================================
# FUEL CONSTANTS
# ============================================================================

# Stoichiometric AFRs
STOICH = {
    "91": 14.7,
    "93": 14.7,
    "98": 14.7,
    "E85": 9.76,
    "Methanol": 6.45,
    "Flex": 12.5,  # blended assumption; refined via ethanol_pct
}

# Fuel density g/cc
FUEL_DENSITY = {
    "91": 0.745,
    "93": 0.748,
    "98": 0.755,
    "E85": 0.781,
    "Methanol": 0.792,
    "Flex": 0.760,
}

# Energy content effect on rough HP per kg of fuel — used for adequacy checks
FUEL_BSFC = {
    "91": 0.50,
    "93": 0.50,
    "98": 0.48,
    "E85": 0.60,
    "Methanol": 0.95,
    "Flex": 0.54,
}

# Octane equivalent (for knock model)
OCTANE = {
    "91": 91,
    "93": 93,
    "98": 98,
    "E85": 105,
    "Methanol": 115,
    "Flex": 100,
}


# ============================================================================
# HELPERS
# ============================================================================

def _round_to(value: float, digits: int) -> float:
    return round(value, digits)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _fuel_density(fuel_type: str, ethanol_pct: float | None) -> float:
    if fuel_type == "Flex" and ethanol_pct is not None:
        e = ethanol_pct / 100.0
        return 0.745 * (1 - e) + 0.781 * e
    return FUEL_DENSITY.get(fuel_type, 0.748)


def _stoich(fuel_type: str, ethanol_pct: float | None) -> float:
    if fuel_type == "Flex" and ethanol_pct is not None:
        e = ethanol_pct / 100.0
        return 14.7 * (1 - e) + 9.76 * e
    return STOICH.get(fuel_type, 14.7)


def _octane(fuel_type: str, ethanol_pct: float | None) -> int:
    if fuel_type == "Flex" and ethanol_pct is not None:
        e = ethanol_pct / 100.0
        return int(91 * (1 - e) + 105 * e)
    return OCTANE.get(fuel_type, 93)


# ============================================================================
# VE CURVE
# ============================================================================

def estimate_ve_curve(displacement_l: float,
                       induction: str,
                       cam_aggressiveness: float = 0.0) -> list[dict[str, float]]:
    """
    Returns VE estimate per RPM cell (0.0 - 1.2 range).
    Parabolic curve centered on a torque peak that shifts with induction.
    """
    if induction == "NA":
        peak_rpm = 4400 + cam_aggressiveness * 800
        peak_ve = 0.92 + cam_aggressiveness * 0.04
    elif induction == "Supercharged":
        peak_rpm = 4000
        peak_ve = 1.18
    else:  # Turbo
        peak_rpm = 4800
        peak_ve = 1.22

    curve = []
    for rpm in RPM_AXIS:
        # Parabolic fall-off; idle suppressed, top-end rolls off
        delta = (rpm - peak_rpm) / 2800.0
        ve = peak_ve * math.exp(-1.4 * delta * delta)
        # idle suppression
        if rpm < 1200:
            ve *= 0.65 + 0.3 * (rpm - 800) / 400
        ve = _clamp(ve, 0.30, peak_ve)
        curve.append({"rpm": rpm, "ve": _round_to(ve, 3)})
    return curve


# ============================================================================
# AFR TARGET TABLE
# ============================================================================

def build_afr_target_table(load_axis: list[int],
                            fuel_type: str,
                            ethanol_pct: float | None,
                            induction: str,
                            afr_bias: float = 0.0) -> list[list[float]]:
    """
    AFR target per (RPM x MAP). afr_bias: -1.0 (richer) .. +1.0 (leaner), clamped to safe band.
    """
    s = _stoich(fuel_type, ethanol_pct)
    rich_floor = s * 0.78   # ~ 11.5 for gas
    lean_cruise = s         # stoich for cruise
    boosted = induction in ("Turbo", "Supercharged")

    table = []
    for _ in RPM_AXIS:
        row = []
        for load in load_axis:
            if load < 35:
                base = lean_cruise * 1.00  # idle/decel
            elif load < 60:
                base = lean_cruise * 0.98  # cruise
            elif load < 80:
                base = s * 0.92            # mid-load enrichment
            elif load < 100:
                base = s * 0.86            # WOT NA
            else:
                # boost zone — richer for charge cooling
                excess = (load - 100) / 100.0
                base = s * (0.84 - 0.06 * excess)

            if boosted and load > 90:
                base *= 0.985  # extra margin under boost

            # bias clamped: never richer than rich_floor, never leaner than stoich
            biased = base * (1.0 + afr_bias * 0.05)
            biased = _clamp(biased, rich_floor, s * 1.02)
            row.append(_round_to(biased, 2))
        table.append(row)
    return table


# ============================================================================
# FUEL MAP (Injector Pulse Width, ms)
# ============================================================================

def build_fuel_map(displacement_l: float,
                    cylinders: int,
                    injector_cc: float,
                    fuel_type: str,
                    ethanol_pct: float | None,
                    induction: str,
                    load_axis: list[int],
                    ve_curve: list[dict[str, float]],
                    afr_table: list[list[float]]) -> list[list[float]]:
    """
    Computes injector pulse width per (RPM x MAP) using ideal gas + mass balance.

    Air mass per intake event per cylinder:
        m_air = MAP[kPa] * 1000 * (displacement_L / cylinders) * VE / (R * T) / 1000
        where R = 287 J/kg.K, T ~= 313 K (intake charge)

    Fuel mass = m_air / AFR_target
    Pulse width (ms) = m_fuel / (injector_flow_kg_per_ms)
    """
    R = 287.0
    T = 313.0
    inj_kg_per_ms = (injector_cc / 60000.0) * _fuel_density(fuel_type, ethanol_pct) * 0.001  # cc/min → kg/ms

    cyl_disp_m3 = (displacement_l / cylinders) / 1000.0
    fuel_density = _fuel_density(fuel_type, ethanol_pct)

    table = []
    for r_idx, ve_row in enumerate(ve_curve):
        ve = ve_row["ve"]
        row = []
        for l_idx, load in enumerate(load_axis):
            map_pa = load * 1000.0
            air_density = map_pa / (R * T)  # kg/m^3
            m_air_per_event = air_density * cyl_disp_m3 * ve  # kg
            afr = afr_table[r_idx][l_idx]
            m_fuel = m_air_per_event / afr  # kg
            pw_ms = m_fuel / inj_kg_per_ms if inj_kg_per_ms > 0 else 0.0
            # Convert: m_fuel is kg, inj_kg_per_ms is kg/ms → pw in ms
            # But our formula is air mass per cylinder per intake event, fuel per event:
            # pulse width should be fuel_mass / injector_mass_flow_per_ms
            row.append(_round_to(pw_ms, 3))
        table.append(row)

    _ = fuel_density  # reserved for future advanced models
    return table


# ============================================================================
# IGNITION MAP (degrees BTDC)
# ============================================================================

def build_ignition_map(load_axis: list[int],
                        fuel_type: str,
                        ethanol_pct: float | None,
                        compression_ratio: float,
                        induction: str,
                        timing_bias: float = 0.0) -> list[list[float]]:
    """
    Conservative MBT estimate, knock-margin adjusted.

    Light load:    high advance (28-38 deg)
    Mid load:      moderate advance (18-26 deg)
    WOT NA:        moderate advance (24-30 deg)
    Boost:         pulled timing (8-18 deg, scaled by boost)

    timing_bias: -1.0 conservative ... +1.0 aggressive (still bounded)
    """
    octane = _octane(fuel_type, ethanol_pct)
    octane_factor = (octane - 91) * 0.6  # +6 deg headroom at E85, -0 at 91
    cr_factor = max(0.0, (compression_ratio - 9.0) * 1.2)  # high CR pulls timing
    bias_gain = 3.0  # +/- 3 deg max bias swing

    table = []
    for rpm in RPM_AXIS:
        row = []
        for load in load_axis:
            if load < 30:
                base = 32.0 - cr_factor + octane_factor * 0.4
            elif load < 55:
                base = 26.0 - cr_factor + octane_factor * 0.4
            elif load < 80:
                base = 22.0 - cr_factor + octane_factor * 0.5
            elif load < 100:
                base = 18.0 - cr_factor * 1.1 + octane_factor * 0.5
            else:
                # boost zone — pull timing aggressively
                excess = (load - 100) / 100.0
                base = 14.0 - cr_factor * 1.3 - excess * 7.0 + octane_factor * 0.7

            # RPM trim — slight advance at higher RPM (need more burn time)
            base += (rpm - 3200) / 1000.0 * 0.4

            # Knock-safety floor & ceiling
            if induction != "NA" and load > 100:
                base = _clamp(base, 4.0, 22.0)
            else:
                base = _clamp(base, 6.0, 38.0)

            base += timing_bias * bias_gain
            row.append(_round_to(base, 1))
        table.append(row)
    return table


# ============================================================================
# BOOST TARGET TABLE
# ============================================================================

def build_boost_target_table(induction: str,
                              boost_ceiling_kpa: float,
                              spool_rpm: int = 3000,
                              boost_intent: float = 0.0) -> list[dict[str, float]] | None:
    """
    Boost target per RPM. None for NA engines.
    boost_intent: -1.0 conservative ... +1.0 aggressive (still capped to ceiling).
    """
    if induction == "NA":
        return None

    target_peak = boost_ceiling_kpa * (0.80 + 0.15 * boost_intent)
    target_peak = _clamp(target_peak, 10.0, boost_ceiling_kpa)

    table = []
    for rpm in RPM_AXIS:
        if rpm < spool_rpm - 800:
            tgt = 0.0
        elif rpm < spool_rpm:
            tgt = target_peak * 0.20
        elif rpm < spool_rpm + 800:
            tgt = target_peak * 0.75
        elif rpm < 5600:
            tgt = target_peak
        else:
            # taper at high RPM to protect turbo / heat
            taper = (rpm - 5600) / 1200.0
            tgt = target_peak * (1.0 - 0.18 * _clamp(taper, 0.0, 1.0))
        table.append({"rpm": rpm, "boost_kpa": _round_to(tgt, 1)})
    return table


# ============================================================================
# IDLE / COLD START TABLES
# ============================================================================

def build_idle_table(fuel_type: str, ethanol_pct: float | None) -> dict[str, Any]:
    """Idle target RPM + base injector duty by CLT."""
    s = _stoich(fuel_type, ethanol_pct)
    base_pw = {
        -20: 6.8,
        -10: 5.4,
        0: 4.2,
        20: 3.0,
        40: 2.4,
        60: 2.0,
        80: 1.6,
        95: 1.5,
    }
    idle_target_rpm = {
        -20: 1500,
        -10: 1400,
        0: 1300,
        20: 1150,
        40: 1000,
        60: 900,
        80: 850,
        95: 850,
    }
    afr_by_clt = {
        -20: s * 0.80,
        -10: s * 0.84,
        0: s * 0.88,
        20: s * 0.93,
        40: s * 0.96,
        60: s * 0.99,
        80: s * 1.00,
        95: s * 1.00,
    }
    return {
        "clt_axis": CLT_AXIS,
        "idle_target_rpm": [idle_target_rpm[c] for c in CLT_AXIS],
        "idle_base_pw_ms": [_round_to(base_pw[c], 2) for c in CLT_AXIS],
        "idle_afr_target": [_round_to(afr_by_clt[c], 2) for c in CLT_AXIS],
    }


def build_cold_start_table(fuel_type: str) -> dict[str, Any]:
    enrichment_pct = {
        -20: 65,
        -10: 50,
        0: 38,
        20: 22,
        40: 12,
        60: 6,
        80: 2,
        95: 0,
    }
    decay_seconds = {
        -20: 60,
        -10: 45,
        0: 35,
        20: 20,
        40: 10,
        60: 5,
        80: 2,
        95: 0,
    }
    return {
        "clt_axis": CLT_AXIS,
        "enrichment_pct": [enrichment_pct[c] for c in CLT_AXIS],
        "decay_seconds": [decay_seconds[c] for c in CLT_AXIS],
        "notes": f"Cold-start enrichment baseline for {fuel_type}. Tapers to zero at operating temp.",
    }


# ============================================================================
# SAFETY ENVELOPE
# ============================================================================

@dataclass
class SafetyEnvelope:
    afr_min: float
    afr_max: float
    ignition_ceiling: float
    boost_ceiling_kpa: float | None
    torque_baseline_nm: float
    knock_sensitivity: str        # low / moderate / high
    thermal_risk: str             # low / moderate / high / extreme
    injector_headroom_pct: float
    fuel_system_adequate: bool
    warnings: list[dict[str, Any]]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "afr_min": self.afr_min,
            "afr_max": self.afr_max,
            "ignition_ceiling": self.ignition_ceiling,
            "boost_ceiling_kpa": self.boost_ceiling_kpa,
            "torque_baseline_nm": self.torque_baseline_nm,
            "knock_sensitivity": self.knock_sensitivity,
            "thermal_risk": self.thermal_risk,
            "injector_headroom_pct": self.injector_headroom_pct,
            "fuel_system_adequate": self.fuel_system_adequate,
            "warnings": self.warnings,
            "confidence": self.confidence,
        }


def compute_safety_envelope(intake: dict[str, Any]) -> SafetyEnvelope:
    fuel_type = intake.get("fuel_type", "93")
    ethanol_pct = intake.get("ethanol_pct")
    induction = intake.get("induction", "NA")
    displacement = float(intake.get("displacement_l", 2.0))
    cylinders = int(intake.get("cylinders", 4))
    target_hp = float(intake.get("target_hp", 250))
    rev_limit = int(intake.get("rev_limit", 6800))
    injector_cc = float(intake.get("injector_cc", 440))
    compression_ratio = float(intake.get("compression_ratio", 10.0))
    intercooler_class = intake.get("intercooler_class", "Stock")

    s = _stoich(fuel_type, ethanol_pct)
    octane = _octane(fuel_type, ethanol_pct)

    # AFR safe band
    afr_min = _round_to(s * 0.78, 2)
    afr_max = _round_to(s * 1.02, 2)

    # Ignition ceiling — conservative MBT cap
    ignition_ceiling = 30.0 + (octane - 91) * 0.3 - max(0, (compression_ratio - 9.5) * 1.5)
    if induction != "NA":
        ignition_ceiling -= 4.0
    ignition_ceiling = _round_to(_clamp(ignition_ceiling, 18.0, 38.0), 1)

    # Boost ceiling
    boost_ceiling = None
    if induction != "NA":
        # base on octane + IC class + compression ratio
        base = 180.0  # ~1.16 bar absolute
        if octane >= 100:
            base += 35
        elif octane <= 91:
            base -= 25
        if compression_ratio >= 10.5:
            base -= 15
        if compression_ratio <= 8.8:
            base += 20
        ic_bonus = {"None": -15, "Stock": 0, "Upgraded": 12, "Race": 22}
        base += ic_bonus.get(intercooler_class, 0)
        boost_ceiling = _round_to(_clamp(base, 110.0, 280.0), 1)

    # Torque baseline (very rough): T_nm ~= displacement_L * peak_BMEP / (4π)
    # For NA gas BMEP ~ 1100 kPa; for turbo ~ 1700 kPa
    bmep = {"NA": 1100, "Turbo": 1700, "Supercharged": 1500}.get(induction, 1100)
    torque_nm = displacement / 1000.0 * bmep * 1000 / (4 * math.pi) * 1000  # rough
    torque_nm = _round_to(displacement * bmep / 12.566, 1)

    # Knock sensitivity
    knock_score = (12 - octane / 8) + (compression_ratio - 9) * 0.8
    if induction != "NA":
        knock_score += 1.5
    if knock_score < 1.5:
        knock_sens = "low"
    elif knock_score < 3.5:
        knock_sens = "moderate"
    else:
        knock_sens = "high"

    # Thermal risk
    hp_per_l = target_hp / max(displacement, 0.1)
    if hp_per_l < 90:
        thermal = "low"
    elif hp_per_l < 140:
        thermal = "moderate"
    elif hp_per_l < 200:
        thermal = "high"
    else:
        thermal = "extreme"

    # Injector adequacy: required fuel kg/h at target HP
    bsfc = FUEL_BSFC.get(fuel_type, 0.50)
    required_lb_h = target_hp * bsfc
    required_cc_min = (required_lb_h * 453.6) / 60.0 / _fuel_density(fuel_type, ethanol_pct)
    per_inj_cc = required_cc_min / max(cylinders, 1)
    headroom = (1 - per_inj_cc / max(injector_cc * 0.85, 1)) * 100
    inj_headroom_pct = _round_to(headroom, 1)
    fuel_adequate = inj_headroom_pct > 5.0

    # Warnings
    warnings: list[dict[str, Any]] = []
    if not fuel_adequate:
        warnings.append({
            "level": "danger",
            "code": "INJECTOR_UNDERSIZED",
            "message": (
                f"Injectors undersized for {int(target_hp)} hp on {fuel_type}. "
                f"Required ~{per_inj_cc:.0f} cc/min per cyl, available {injector_cc:.0f} cc/min @ 85% duty."
            ),
        })
    elif inj_headroom_pct < 15:
        warnings.append({
            "level": "warning",
            "code": "INJECTOR_MARGINAL",
            "message": f"Injector duty cycle margin only {inj_headroom_pct:.0f}%. Consider larger injectors.",
        })

    if thermal == "extreme":
        warnings.append({
            "level": "danger",
            "code": "THERMAL_EXTREME",
            "message": f"Target {target_hp:.0f} hp on {displacement:.1f}L is extreme ({hp_per_l:.0f} hp/L). Reduce target or upgrade cooling.",
        })
    elif thermal == "high":
        warnings.append({
            "level": "warning",
            "code": "THERMAL_HIGH",
            "message": f"High thermal load ({hp_per_l:.0f} hp/L). Validate intercooler and oil cooling.",
        })

    if knock_sens == "high":
        warnings.append({
            "level": "warning",
            "code": "KNOCK_RISK_HIGH",
            "message": f"High knock risk: octane {octane}, CR {compression_ratio:.1f}. Timing will be pulled conservatively.",
        })

    if rev_limit > 7200 and induction == "NA":
        warnings.append({
            "level": "warning",
            "code": "REV_LIMIT_HIGH",
            "message": "Rev limit above 7200 RPM requires valvetrain validation.",
        })

    if induction != "NA" and boost_ceiling is not None and target_hp > displacement * 110:
        warnings.append({
            "level": "warning",
            "code": "AGGRESSIVE_TARGET",
            "message": f"Aggressive HP target ({target_hp:.0f} hp). Starter tune will cap to safety envelope.",
        })

    # Confidence
    confidence = 0.95
    if intake.get("injector_cc") is None:
        confidence -= 0.10
    if intake.get("compression_ratio") is None:
        confidence -= 0.08
    if intake.get("map_sensor_kpa") is None:
        confidence -= 0.04
    confidence -= len([w for w in warnings if w["level"] == "danger"]) * 0.10
    confidence -= len([w for w in warnings if w["level"] == "warning"]) * 0.04
    confidence = _round_to(_clamp(confidence, 0.25, 0.98), 2)

    return SafetyEnvelope(
        afr_min=afr_min,
        afr_max=afr_max,
        ignition_ceiling=ignition_ceiling,
        boost_ceiling_kpa=boost_ceiling,
        torque_baseline_nm=torque_nm,
        knock_sensitivity=knock_sens,
        thermal_risk=thermal,
        injector_headroom_pct=inj_headroom_pct,
        fuel_system_adequate=fuel_adequate,
        warnings=warnings,
        confidence=confidence,
    )


# ============================================================================
# CONFIDENCE SCORING
# ============================================================================

def score_confidence(intake: dict[str, Any],
                      envelope: SafetyEnvelope) -> dict[str, float]:
    """Per-subsystem confidence."""
    base = envelope.confidence
    return {
        "overall": base,
        "fuel": _round_to(_clamp(base + (0.02 if intake.get("injector_cc") else -0.10), 0.2, 0.98), 2),
        "ignition": _round_to(_clamp(base + (0.03 if intake.get("compression_ratio") else -0.08), 0.2, 0.98), 2),
        "boost": _round_to(_clamp(base - (0.04 if intake.get("induction") != "NA" else 0.0), 0.2, 0.98), 2),
        "idle": _round_to(_clamp(base - 0.05, 0.2, 0.95), 2),
        "safety": _round_to(envelope.confidence, 2),
    }


# ============================================================================
# PREDICTED HORSEPOWER
# ============================================================================

def predict_hp(intake: dict[str, Any]) -> dict[str, float]:
    """Rough predicted HP range from displacement / induction / fuel."""
    displacement = float(intake.get("displacement_l", 2.0))
    induction = intake.get("induction", "NA")
    fuel_type = intake.get("fuel_type", "93")
    rev_limit = int(intake.get("rev_limit", 6800))

    base_hp_per_l = {"NA": 75, "Supercharged": 130, "Turbo": 155}.get(induction, 75)
    fuel_bonus = {"E85": 1.10, "Methanol": 1.18, "98": 1.05}.get(fuel_type, 1.0)
    rev_bonus = 1.0 + max(0, (rev_limit - 6500)) / 8000.0

    nominal = displacement * base_hp_per_l * fuel_bonus * rev_bonus
    return {
        "low": _round_to(nominal * 0.85, 0),
        "nominal": _round_to(nominal, 0),
        "high": _round_to(nominal * 1.20, 0),
    }


# ============================================================================
# FULL TUNE PACKAGE
# ============================================================================

def generate_starter_tune(intake: dict[str, Any],
                            adjustments: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Top-level entry. Produces a complete starter tune package.
    """
    adjustments = adjustments or {}
    afr_bias = float(adjustments.get("afr_bias", 0.0))         # -1..+1
    timing_bias = float(adjustments.get("timing_bias", 0.0))   # -1..+1
    boost_intent = float(adjustments.get("boost_intent", 0.0)) # -1..+1
    drivability_bias = float(adjustments.get("drivability_bias", 0.0))  # -1..+1 (toward perf)
    cam_aggressiveness = drivability_bias * 0.4  # used in VE estimate

    envelope = compute_safety_envelope(intake)

    induction = intake.get("induction", "NA")
    boosted = induction in ("Turbo", "Supercharged")
    load_axis = BOOST_LOAD_AXIS if boosted else NA_LOAD_AXIS

    ve_curve = estimate_ve_curve(
        displacement_l=float(intake.get("displacement_l", 2.0)),
        induction=induction,
        cam_aggressiveness=cam_aggressiveness,
    )

    afr_table = build_afr_target_table(
        load_axis=load_axis,
        fuel_type=intake.get("fuel_type", "93"),
        ethanol_pct=intake.get("ethanol_pct"),
        induction=induction,
        afr_bias=afr_bias,
    )

    fuel_map = build_fuel_map(
        displacement_l=float(intake.get("displacement_l", 2.0)),
        cylinders=int(intake.get("cylinders", 4)),
        injector_cc=float(intake.get("injector_cc", 440)),
        fuel_type=intake.get("fuel_type", "93"),
        ethanol_pct=intake.get("ethanol_pct"),
        induction=induction,
        load_axis=load_axis,
        ve_curve=ve_curve,
        afr_table=afr_table,
    )

    ignition_map = build_ignition_map(
        load_axis=load_axis,
        fuel_type=intake.get("fuel_type", "93"),
        ethanol_pct=intake.get("ethanol_pct"),
        compression_ratio=float(intake.get("compression_ratio", 10.0)),
        induction=induction,
        timing_bias=timing_bias,
    )

    # Cap ignition map by ignition ceiling from envelope
    ignition_map = [[min(cell, envelope.ignition_ceiling) for cell in row] for row in ignition_map]

    boost_table = build_boost_target_table(
        induction=induction,
        boost_ceiling_kpa=envelope.boost_ceiling_kpa or 100.0,
        spool_rpm=int(intake.get("spool_rpm", 3000)),
        boost_intent=boost_intent,
    )

    idle = build_idle_table(intake.get("fuel_type", "93"), intake.get("ethanol_pct"))
    cold_start = build_cold_start_table(intake.get("fuel_type", "93"))
    predicted = predict_hp(intake)
    confidence = score_confidence(intake, envelope)

    # Assumptions summary
    assumptions = [
        "Intake charge temp assumed 313K (40°C) for VE-based mass airflow.",
        f"AFR target shaped around {_stoich(intake.get('fuel_type','93'), intake.get('ethanol_pct'))} stoich.",
        f"Octane equivalent: {_octane(intake.get('fuel_type','93'), intake.get('ethanol_pct'))}",
        f"Ignition ceiling capped at {envelope.ignition_ceiling}° BTDC.",
        f"Boost ceiling capped at {envelope.boost_ceiling_kpa} kPa." if boosted else "Naturally aspirated — no boost table generated.",
        "Injector duty target ≤ 85% at peak power.",
    ]

    return {
        "axes": {
            "rpm": RPM_AXIS,
            "load_kpa": load_axis,
            "clt": CLT_AXIS,
            "idle_rpm": IDLE_RPM_AXIS,
        },
        "ve_curve": ve_curve,
        "afr_target_table": afr_table,
        "fuel_map_ms": fuel_map,
        "ignition_map_deg": ignition_map,
        "boost_target_table": boost_table,
        "idle_table": idle,
        "cold_start_table": cold_start,
        "safety_envelope": envelope.to_dict(),
        "confidence": confidence,
        "predicted_hp": predicted,
        "assumptions": assumptions,
        "adjustments_applied": {
            "afr_bias": afr_bias,
            "timing_bias": timing_bias,
            "boost_intent": boost_intent,
            "drivability_bias": drivability_bias,
        },
        "algorithm_version": "starter-tune-engine/1.0",
    }


# ============================================================================
# DIFF / CHANGED CELLS
# ============================================================================

def compute_map_diff(prev: list[list[float]],
                      curr: list[list[float]],
                      threshold: float = 0.001) -> dict[str, Any]:
    if not prev or not curr:
        return {"changed_count": 0, "max_delta": 0.0, "deltas": []}
    deltas = []
    max_delta = 0.0
    changed = 0
    for r, (pr, cr) in enumerate(zip(prev, curr)):
        row = []
        for c, (pv, cv) in enumerate(zip(pr, cr)):
            d = cv - pv
            row.append(round(d, 3))
            if abs(d) > threshold:
                changed += 1
            if abs(d) > abs(max_delta):
                max_delta = d
        deltas.append(row)
    return {
        "changed_count": changed,
        "max_delta": round(max_delta, 3),
        "deltas": deltas,
    }
