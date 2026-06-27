"""Round 2 backend tests — DIAG-SIM, Inspector, knock_pull, deep_links."""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

AGGR_INTAKE = {
    "displacement_l": 2.0,
    "cylinders": 4,
    "induction": "Turbo",
    "fuel_type": "91",
    "target_hp": 500,
    "rev_limit": 7400,
    "injector_cc": 650,
    "compression_ratio": 9.5,
}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers["Content-Type"] = "application/json"
    return sess


@pytest.fixture(scope="module")
def pid(s):
    pkg = s.post(f"{API}/starter-tune/generate", json={"intake": AGGR_INTAKE}).json()
    pr = s.post(f"{API}/profiles", json={
        "name": "TEST_R2_Aggressive",
        "intake": AGGR_INTAKE,
        "tune_package": pkg,
    })
    assert pr.status_code == 200
    profile_id = pr.json()["id"]
    yield profile_id
    s.delete(f"{API}/profiles/{profile_id}")


# === DIAG-SIM ============================================================

def test_diagsim_scenarios(s):
    r = s.get(f"{API}/diagsim/scenarios")
    assert r.status_code == 200
    d = r.json()
    for k in ("wot_pull", "partial_cruise", "idle_dwell", "tip_in"):
        assert k in d, f"missing scenario {k}"


def test_diagsim_run_and_retrieve(s, pid):
    r = s.post(f"{API}/profiles/{pid}/diagsim/run", json={"scenario": "wot_pull", "seed": 42})
    assert r.status_code == 200, r.text
    sess = r.json()
    assert "session_id" in sess
    assert isinstance(sess["samples"], list) and len(sess["samples"]) >= 200
    summary = sess["summary"]
    for k in ("peak_rpm", "peak_boost_kpa_over_atm", "min_afr", "max_afr", "knock_events"):
        assert k in summary, f"summary missing {k}"
    assert isinstance(sess["fault_codes"], list)
    # sample schema
    sample = sess["samples"][0]
    for k in ("t", "rpm", "map_kpa", "tps", "afr_target", "afr_measured",
              "timing_cmd", "knock", "iat", "ect", "boost_kpa"):
        assert k in sample, f"sample missing {k}"

    sid = sess["session_id"]
    # retrieve
    g = s.get(f"{API}/diagsim/sessions/{sid}")
    assert g.status_code == 200
    assert g.json()["session_id"] == sid
    # list
    lst = s.get(f"{API}/profiles/{pid}/diagsim/sessions")
    assert lst.status_code == 200
    arr = lst.json()
    assert any(x["session_id"] == sid for x in arr)
    # lightweight (no samples)
    assert all("samples" not in x for x in arr), "list endpoint should not include samples"


# === INSPECTOR ============================================================

def test_inspector_audit(s, pid):
    r = s.post(f"{API}/profiles/{pid}/inspector/audit")
    assert r.status_code == 200, r.text
    rep = r.json()
    assert 0 <= rep["score"] <= 100
    assert rep["score"] < 80, f"aggressive build should score <80, got {rep['score']}"
    for sub in ("fuel", "ignition", "boost", "safety"):
        assert sub in rep["subsystem_scores"]
    counts = rep["counts"]
    for k in ("critical", "warning", "info"):
        assert k in counts
    assert counts["critical"] + counts["warning"] >= 1, "expected at least 1 critical/warning"
    assert isinstance(rep["findings"], list) and len(rep["findings"]) >= 1
    f0 = rep["findings"][0]
    for k in ("code", "severity", "subsystem", "message", "remediation"):
        assert k in f0
    assert isinstance(rep["recommendations"], list) and len(rep["recommendations"]) >= 1

    # retrieve
    rid = rep["report_id"]
    g = s.get(f"{API}/inspector/reports/{rid}")
    assert g.status_code == 200
    assert g.json()["report_id"] == rid


# === EXPORTS produce REAL artifacts =======================================

def test_export_diagsim_real(s, pid):
    r = s.post(f"{API}/profiles/{pid}/export/diagsim")
    assert r.status_code == 200
    art = r.json()
    sid = art["payload"]["session_id"]
    assert art["deep_link"] == f"/diagsim/{sid}"
    # session must be persisted
    g = s.get(f"{API}/diagsim/sessions/{sid}")
    assert g.status_code == 200


def test_export_inspector_real(s, pid):
    r = s.post(f"{API}/profiles/{pid}/export/inspector")
    assert r.status_code == 200
    art = r.json()
    rid = art["payload"]["report_id"]
    assert art["deep_link"] == f"/inspector/{rid}"
    g = s.get(f"{API}/inspector/reports/{rid}")
    assert g.status_code == 200


def test_export_forensic_single(s, pid):
    # pid only has 1 generation (fresh)
    r = s.post(f"{API}/profiles/{pid}/export/forensic")
    assert r.status_code == 200
    pl = r.json()["payload"]
    assert pl["mode"] == "single_generation_audit"


def test_export_forensic_two_gen(s):
    # build a fresh profile, regenerate once, then forensic
    pkg = s.post(f"{API}/starter-tune/generate", json={"intake": AGGR_INTAKE}).json()
    pr = s.post(f"{API}/profiles", json={
        "name": "TEST_R2_Forensic",
        "intake": AGGR_INTAKE,
        "tune_package": pkg,
    }).json()
    pid2 = pr["id"]
    try:
        rg = s.post(f"{API}/profiles/{pid2}/regenerate", json={
            "intake": AGGR_INTAKE,
            "adjustments": {"afr_bias": -0.5, "timing_bias": 0.3, "boost_intent": 0.3,
                            "drivability_bias": 0.0},
            "note": "TEST",
        })
        assert rg.status_code == 200
        r = s.post(f"{API}/profiles/{pid2}/export/forensic")
        assert r.status_code == 200
        pl = r.json()["payload"]
        assert pl["mode"] == "two_generation_diff"
        assert "fuel_diff" in pl and "ignition_diff" in pl
    finally:
        s.delete(f"{API}/profiles/{pid2}")


def test_export_ecu_payload(s, pid):
    r = s.post(f"{API}/profiles/{pid}/export/ecu")
    assert r.status_code == 200
    pl = r.json()["payload"]
    for k in ("rpm_axis", "load_axis", "fuel_map_ms", "ignition_map_deg",
              "afr_target_table", "idle_table", "cold_start_table", "safety_envelope"):
        assert k in pl, f"ECU payload missing {k}"


# === KNOCK PULL ============================================================

def test_knock_pull_applied(s):
    """High-RPM × peak-load knock pull lowers top-right ignition cells."""
    base = s.post(f"{API}/starter-tune/generate",
                  json={"intake": AGGR_INTAKE}).json()
    base_ign = base["ignition_map_deg"]

    pulled = s.post(f"{API}/starter-tune/generate", json={
        "intake": AGGR_INTAKE,
        "adjustments": {
            "afr_bias": 0.0, "timing_bias": 0.0,
            "boost_intent": 0.0, "drivability_bias": 0.0,
            "knock_pull_zones": [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, -3.0],
                [0, 0, -1.5, -3.0],
            ],
        },
    }).json()
    assert "ignition_map_deg" in pulled
    pulled_ign = pulled["ignition_map_deg"]
    applied = pulled.get("adjustments_applied", {})
    assert applied.get("knock_pull_applied") is True, f"knock_pull_applied missing: {applied}"
    assert applied.get("knock_pull_zones") == [
        [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, -3.0], [0, 0, -1.5, -3.0],
    ]

    # top-right region (high RPM x high load) should drop
    # 16x16 map, zone (3,3) → rows 12..15, cols 12..15
    base_tr = sum(base_ign[r][c] for r in range(12, 16) for c in range(12, 16))
    pulled_tr = sum(pulled_ign[r][c] for r in range(12, 16) for c in range(12, 16))
    assert pulled_tr < base_tr, f"top-right not reduced (base={base_tr}, pulled={pulled_tr})"

    # all cells still >= 0 (floored)
    for row in pulled_ign:
        for v in row:
            assert v >= 0, f"ignition cell {v} < 0"
