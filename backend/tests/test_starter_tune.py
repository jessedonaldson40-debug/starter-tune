"""Backend test suite for the STANDAILONE Starter Tune Engine."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://starter-tune-gen.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

INTAKE = {
    "displacement_l": 2.0,
    "cylinders": 4,
    "induction": "Turbo",
    "fuel_type": "93",
    "target_hp": 350,
    "rev_limit": 7000,
    "injector_cc": 650,
    "compression_ratio": 9.5,
}

AGGR_INTAKE = {
    "displacement_l": 2.0,
    "cylinders": 4,
    "induction": "Turbo",
    "fuel_type": "91",
    "target_hp": 500,
    "rev_limit": 7500,
    "injector_cc": 440,
    "compression_ratio": 10.5,
    "intercooler_class": "Stock",
}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers["Content-Type"] = "application/json"
    return sess


# --- Core endpoints ---

def test_root(s):
    r = s.get(f"{API}/")
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") == "online"
    assert "service" in d


def test_predict_hp(s):
    r = s.post(f"{API}/starter-tune/predict-hp", json=INTAKE)
    assert r.status_code == 200
    d = r.json()
    for k in ("low", "nominal", "high"):
        assert k in d and d[k] > 0
    assert d["low"] <= d["nominal"] <= d["high"]


def test_ve_preview(s):
    r = s.post(f"{API}/starter-tune/ve-preview", json=INTAKE)
    assert r.status_code == 200
    d = r.json()
    assert len(d["ve_curve"]) == 16
    assert len(d["rpm_axis"]) == 16


def test_safety_envelope_aggressive(s):
    r = s.post(f"{API}/starter-tune/safety-envelope", json=AGGR_INTAKE)
    assert r.status_code == 200
    d = r.json()
    codes = {w["code"] for w in d["warnings"]}
    levels = {w["level"] for w in d["warnings"]}
    assert d["warnings"], "Expected warnings for aggressive intake"
    # Expect at least one of the key safety alerts
    expected_any = {"INJECTOR_UNDERSIZED", "THERMAL_HIGH", "THERMAL_EXTREME", "AGGRESSIVE_TARGET"}
    assert codes & expected_any, f"Expected at least one of {expected_any}, got {codes}"
    assert "danger" in levels or "warning" in levels


# --- Generate ---

def test_generate_full_package(s):
    r = s.post(f"{API}/starter-tune/generate", json={"intake": INTAKE})
    assert r.status_code == 200
    pkg = r.json()
    for k in ("axes", "ve_curve", "afr_target_table", "fuel_map_ms",
              "ignition_map_deg", "boost_target_table", "idle_table",
              "cold_start_table", "safety_envelope", "confidence", "predicted_hp"):
        assert k in pkg, f"Missing key {k}"
    # 16x16 maps
    assert len(pkg["fuel_map_ms"]) == 16
    assert all(len(row) == 16 for row in pkg["fuel_map_ms"])
    assert len(pkg["ignition_map_deg"]) == 16
    assert all(len(row) == 16 for row in pkg["ignition_map_deg"])
    # confidence
    overall = pkg["confidence"]["overall"]
    assert 0 < overall <= 1
    # ignition cap
    ceiling = pkg["safety_envelope"]["ignition_ceiling"]
    for row in pkg["ignition_map_deg"]:
        for cell in row:
            assert cell <= ceiling + 1e-6, f"Cell {cell} > ceiling {ceiling}"


# --- Profiles ---

@pytest.fixture(scope="module")
def profile_ctx(s):
    pkg = s.post(f"{API}/starter-tune/generate", json={"intake": INTAKE}).json()
    create = s.post(f"{API}/profiles", json={
        "name": "TEST_StarterProfile",
        "intake": INTAKE,
        "tune_package": pkg,
    })
    assert create.status_code == 200
    pid = create.json()["id"]
    yield pid
    # cleanup
    s.delete(f"{API}/profiles/{pid}")


def test_profile_create_list_get(s, profile_ctx):
    pid = profile_ctx
    lst = s.get(f"{API}/profiles")
    assert lst.status_code == 200
    assert any(p["id"] == pid for p in lst.json())
    detail = s.get(f"{API}/profiles/{pid}")
    assert detail.status_code == 200
    d = detail.json()
    assert len(d["history"]) == 1
    assert d["active_generation_index"] == 0


def test_profile_regenerate_and_compare(s, profile_ctx):
    pid = profile_ctx
    r = s.post(f"{API}/profiles/{pid}/regenerate", json={
        "intake": INTAKE,
        "adjustments": {"afr_bias": -0.5, "timing_bias": 0.3, "boost_intent": 0.4, "drivability_bias": 0.2},
        "note": "TEST regenerate",
    })
    assert r.status_code == 200
    entry = r.json()
    assert entry["generation_index"] == 1
    assert entry["diff_vs_previous"]["fuel"]["changed_count"] > 0

    # check profile state
    detail = s.get(f"{API}/profiles/{pid}").json()
    assert len(detail["history"]) == 2
    assert detail["active_generation_index"] == 1

    cmp_r = s.get(f"{API}/profiles/{pid}/compare/0/1")
    assert cmp_r.status_code == 200
    cd = cmp_r.json()
    assert cd["fuel_diff"]["changed_count"] > 0 or cd["ignition_diff"]["changed_count"] > 0


def test_profile_revert(s, profile_ctx):
    pid = profile_ctx
    r = s.post(f"{API}/profiles/{pid}/revert/0")
    assert r.status_code == 200
    assert r.json()["active_generation_index"] == 0
    d = s.get(f"{API}/profiles/{pid}").json()
    assert d["active_generation_index"] == 0


@pytest.mark.parametrize("target", ["diagsim", "inspector", "forensic", "ecu"])
def test_profile_export(s, profile_ctx, target):
    pid = profile_ctx
    before = len(s.get(f"{API}/profiles/{pid}").json().get("exports", []))
    r = s.post(f"{API}/profiles/{pid}/export/{target}")
    assert r.status_code == 200
    a = r.json()
    assert "artifact_id" in a
    assert "format" in a
    assert "payload" in a
    after = len(s.get(f"{API}/profiles/{pid}").json().get("exports", []))
    assert after == before + 1


def test_profile_delete(s):
    pkg = s.post(f"{API}/starter-tune/generate", json={"intake": INTAKE}).json()
    pid = s.post(f"{API}/profiles", json={
        "name": "TEST_DeleteMe",
        "intake": INTAKE,
        "tune_package": pkg,
    }).json()["id"]
    r = s.delete(f"{API}/profiles/{pid}")
    assert r.status_code == 200
    g = s.get(f"{API}/profiles/{pid}")
    assert g.status_code == 404
