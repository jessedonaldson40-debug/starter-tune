"""
STANDAILONE DIAG-SIM — Synthetic Telemetry Simulator
====================================================
Given a tune package and a scenario, produce a credible time-series of
RPM / MAP / TPS / AFR / commanded timing / knock events / IAT / ECT / boost /
fuel trim — exactly the kind of telemetry the real DIAG-SIM module would
emit on a CAN/OBD stream.

This is NOT a mock dump. The simulator:
  - sweeps RPM through a scenario (WOT pull, partial-throttle cruise, idle dwell)
  - looks up commanded values from the tune's actual maps
  - synthesizes plausible measured AFR / timing actual with Gaussian noise + bias
  - rolls a knock probability per sample driven by load × CR-deficit × timing-headroom
  - escalates to fault codes when knock event density crosses thresholds
"""
from __future__ import annotations

import math
import random
from typing import Any


# ---------------------------------------------------------------------------
# Helpers — bilinear lookup of a 16×16 map by physical (rpm, load_kpa)
# ---------------------------------------------------------------------------

def _interp1d(axis: list[float], value: float) -> tuple[int, int, float]:
    """Return (lo_idx, hi_idx, frac) for a 1D axis lookup."""
    if value <= axis[0]:
        return 0, 0, 0.0
    if value >= axis[-1]:
        return len(axis) - 1, len(axis) - 1, 0.0
    for i in range(len(axis) - 1):
        if axis[i] <= value <= axis[i + 1]:
            span = axis[i + 1] - axis[i] or 1.0
            return i, i + 1, (value - axis[i]) / span
    return 0, 0, 0.0


def map_lookup(matrix: list[list[float]],
                rpm_axis: list[int], load_axis: list[int],
                rpm: float, load_kpa: float) -> float:
    r_lo, r_hi, r_f = _interp1d([float(x) for x in rpm_axis], rpm)
    l_lo, l_hi, l_f = _interp1d([float(x) for x in load_axis], load_kpa)
    a = matrix[r_lo][l_lo] * (1 - l_f) + matrix[r_lo][l_hi] * l_f
    b = matrix[r_hi][l_lo] * (1 - l_f) + matrix[r_hi][l_hi] * l_f
    return a * (1 - r_f) + b * r_f


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

SCENARIOS = {
    "wot_pull": {
        "name": "WOT 4th-gear pull",
        "description": "Full-throttle pull from 2200 to peak RPM over 8 seconds.",
        "duration_s": 8.0,
        "sample_hz": 50,
    },
    "partial_cruise": {
        "name": "Steady-state cruise",
        "description": "60% throttle cruise at ~3200 RPM, light load.",
        "duration_s": 6.0,
        "sample_hz": 50,
    },
    "idle_dwell": {
        "name": "Idle dwell",
        "description": "Closed-throttle idle at operating temp.",
        "duration_s": 6.0,
        "sample_hz": 25,
    },
    "tip_in": {
        "name": "Throttle tip-in",
        "description": "Sudden tip-in from cruise to WOT.",
        "duration_s": 5.0,
        "sample_hz": 50,
    },
}


def _scenario_curves(scenario: str, intake: dict[str, Any]) -> dict[str, Any]:
    rev_limit = int(intake.get("rev_limit", 6800))
    induction = intake.get("induction", "NA")
    spool = int(intake.get("spool_rpm", 3000))
    peak_load = 240 if induction != "NA" else 100

    if scenario == "wot_pull":
        def rpm_at(t):
            # ramp 2200 -> rev_limit-200 over duration
            return 2200 + (rev_limit - 200 - 2200) * (t / 8.0)

        def map_at(t, rpm):
            if induction == "NA":
                return min(peak_load, 30 + 70 * (t / 8.0))
            # turbo: spool curve
            spool_t = max(0.05, min(1.0, (rpm - spool + 500) / 1500))
            return min(peak_load, 35 + (peak_load - 35) * spool_t)

        def tps_at(t): return 100.0

    elif scenario == "partial_cruise":
        def rpm_at(t): return 3200 + math.sin(t) * 40
        def map_at(t, rpm): return 55 + math.sin(t * 0.7) * 4
        def tps_at(t): return 35 + math.sin(t * 0.9) * 4

    elif scenario == "idle_dwell":
        def rpm_at(t): return 880 + math.sin(t * 1.3) * 14
        def map_at(t, rpm): return 28 + math.sin(t * 1.1) * 2
        def tps_at(t): return 1.5

    else:  # tip_in
        def rpm_at(t):
            return 2800 + (rev_limit - 1000 - 2800) * min(1.0, max(0.0, (t - 0.5) / 3.5))

        def map_at(t, rpm):
            if t < 0.5:
                return 40
            if induction == "NA":
                return min(peak_load, 40 + 60 * min(1.0, (t - 0.5) / 1.2))
            return min(peak_load, 40 + (peak_load - 40) * min(1.0, (t - 0.5) / 1.6))

        def tps_at(t): return 30 if t < 0.5 else 100

    return {"rpm_at": rpm_at, "map_at": map_at, "tps_at": tps_at}


# ---------------------------------------------------------------------------
# Main simulator
# ---------------------------------------------------------------------------

def simulate(tune_package: dict[str, Any],
              intake: dict[str, Any],
              scenario: str = "wot_pull",
              seed: int | None = None) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        scenario = "wot_pull"
    meta = SCENARIOS[scenario]
    rng = random.Random(seed if seed is not None else 1337)
    curves = _scenario_curves(scenario, intake)

    rpm_axis = tune_package["axes"]["rpm"]
    load_axis = tune_package["axes"]["load_kpa"]
    fuel_map = tune_package["fuel_map_ms"]
    ign_map = tune_package["ignition_map_deg"]
    afr_table = tune_package["afr_target_table"]
    envelope = tune_package["safety_envelope"]

    compression_ratio = float(intake.get("compression_ratio", 10.0))
    octane_def = max(0.0, (10.0 - {"91": 91, "93": 93, "98": 98, "E85": 105, "Methanol": 115, "Flex": 100}.get(intake.get("fuel_type", "93"), 93) / 9.5))
    boost_ceiling = envelope.get("boost_ceiling_kpa") or 100.0

    duration = meta["duration_s"]
    hz = meta["sample_hz"]
    n_samples = int(duration * hz)
    dt = duration / max(1, n_samples)

    samples = []
    iat = 32.0
    ect = 88.0
    knock_window = []  # rolling 1-second window of knock counts
    knock_total = 0
    fuel_trim = 0.0
    boost_actual = 0.0

    for i in range(n_samples):
        t = i * dt
        rpm = max(600, curves["rpm_at"](t))
        load = max(20, curves["map_at"](t, rpm))
        tps = curves["tps_at"](t)

        # Commanded values from tune
        pw_ms = map_lookup(fuel_map, rpm_axis, load_axis, rpm, load)
        timing_cmd = map_lookup(ign_map, rpm_axis, load_axis, rpm, load)
        afr_target = map_lookup(afr_table, rpm_axis, load_axis, rpm, load)

        # Synthesize measured AFR with closed-loop bias + noise
        afr_noise = rng.gauss(0, 0.08)
        afr_measured = afr_target + fuel_trim + afr_noise

        # Boost actual lags command a bit
        boost_target = max(0.0, load - 100)
        boost_actual += (boost_target - boost_actual) * 0.18
        boost_kpa_above = max(0.0, load - 100)

        # Knock probability — driven by:
        #   high load × low octane × timing approaching MBT × elevated IAT
        timing_headroom = max(0.0, envelope["ignition_ceiling"] - timing_cmd)
        load_factor = max(0.0, (load - 80) / 100.0)
        knock_prob = (
            0.0008
            + 0.012 * load_factor
            + 0.018 * octane_def * load_factor
            + 0.004 * max(0.0, (compression_ratio - 10) / 2.0)
            + 0.001 * max(0.0, iat - 45) * load_factor
            - 0.006 * timing_headroom * 0.1
        )
        knock_prob = max(0.0, min(0.15, knock_prob))
        # Heavy pull (zone with knock_pull applied) suppresses knock
        if timing_cmd < 8.0 and load > 120:
            knock_prob *= 0.25

        knock = 1 if rng.random() < knock_prob else 0

        # IAT / ECT drift with load
        iat += (28 + load_factor * 22 - iat) * 0.02 + rng.gauss(0, 0.15)
        ect += (88 + load_factor * 8 - ect) * 0.012 + rng.gauss(0, 0.08)

        # Closed-loop fuel trim slowly corrects toward target
        if scenario != "wot_pull" or load < 80:
            fuel_trim += (afr_target - afr_measured) * 0.02

        knock_window.append(knock)
        if len(knock_window) > hz:
            knock_window.pop(0)
        knock_total += knock

        samples.append({
            "t": round(t, 3),
            "rpm": round(rpm, 0),
            "map_kpa": round(load, 1),
            "tps": round(tps, 1),
            "afr_target": round(afr_target, 2),
            "afr_measured": round(afr_measured, 2),
            "timing_cmd": round(timing_cmd, 1),
            "knock": knock,
            "iat": round(iat, 1),
            "ect": round(ect, 1),
            "boost_kpa": round(boost_kpa_above, 1),
            "pw_ms": round(pw_ms, 3),
        })

    # Summary + faults
    afr_min = min(s["afr_measured"] for s in samples)
    afr_max = max(s["afr_measured"] for s in samples)
    timing_max = max(s["timing_cmd"] for s in samples)
    peak_boost = max(s["boost_kpa"] for s in samples)
    peak_rpm = max(s["rpm"] for s in samples)

    fault_codes = []
    if knock_total >= 6:
        fault_codes.append({
            "code": "P0325",
            "label": "Knock sensor circuit / repeated knock detection",
            "severity": "warning",
            "count": knock_total,
        })
    if afr_min < envelope["afr_min"] * 0.95:
        fault_codes.append({
            "code": "P0172",
            "label": f"System too rich (measured AFR {afr_min:.2f} below floor {envelope['afr_min']:.2f})",
            "severity": "info",
        })
    if afr_max > envelope["afr_max"] * 1.03:
        fault_codes.append({
            "code": "P0171",
            "label": f"System too lean (measured AFR {afr_max:.2f} above ceiling {envelope['afr_max']:.2f})",
            "severity": "danger",
        })
    if peak_boost > boost_ceiling - 100:  # boost_ceiling is absolute, we report above-atmospheric
        # near ceiling
        if peak_boost > (boost_ceiling - 100) * 1.02:
            fault_codes.append({
                "code": "P0234",
                "label": f"Overboost approaching envelope ceiling ({peak_boost:.0f} kPa over atm)",
                "severity": "warning",
            })

    return {
        "scenario": scenario,
        "scenario_name": meta["name"],
        "scenario_description": meta["description"],
        "duration_s": duration,
        "sample_hz": hz,
        "samples": samples,
        "summary": {
            "min_afr": round(afr_min, 2),
            "max_afr": round(afr_max, 2),
            "max_timing": round(timing_max, 1),
            "peak_boost_kpa_over_atm": round(peak_boost, 1),
            "peak_rpm": round(peak_rpm, 0),
            "knock_events": knock_total,
            "n_samples": len(samples),
        },
        "fault_codes": fault_codes,
    }
