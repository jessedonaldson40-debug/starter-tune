"""Round 3 backend tests — export refactor regression, inspector report enrichment, AI Explainer SSE."""
import os
import json
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
        "name": "TEST_R3_Aggressive",
        "intake": AGGR_INTAKE,
        "tune_package": pkg,
    })
    assert pr.status_code == 200
    profile_id = pr.json()["id"]
    yield profile_id
    s.delete(f"{API}/profiles/{profile_id}")


# === EXPORT REFACTOR — verify all 4 helpers still behave correctly ==========

def test_export_diagsim_refactored(s, pid):
    r = s.post(f"{API}/profiles/{pid}/export/diagsim")
    assert r.status_code == 200, r.text
    art = r.json()
    sid = art["payload"]["session_id"]
    assert art["deep_link"] == f"/diagsim/{sid}"
    # persisted in profile.exports
    prof = s.get(f"{API}/profiles/{pid}").json()
    assert any(e.get("artifact_id") == art["artifact_id"] for e in prof.get("exports", []))


def test_export_inspector_refactored(s, pid):
    r = s.post(f"{API}/profiles/{pid}/export/inspector")
    assert r.status_code == 200, r.text
    art = r.json()
    rid = art["payload"]["report_id"]
    assert art["deep_link"] == f"/inspector/{rid}"
    # GET inspector report — must include engine_metadata + safety_envelope
    g = s.get(f"{API}/inspector/reports/{rid}").json()
    assert "engine_metadata" in g, "inspector report missing engine_metadata"
    assert "safety_envelope" in g, "inspector report missing safety_envelope"
    assert g["engine_metadata"]["displacement_l"] == 2.0
    assert "boost_ceiling_kpa" in g["safety_envelope"]


def test_export_forensic_refactored(s, pid):
    r = s.post(f"{API}/profiles/{pid}/export/forensic")
    assert r.status_code == 200
    art = r.json()
    assert art["deep_link"] == f"/profiles/{pid}/compare"
    assert "mode" in art["payload"]


def test_export_ecu_refactored(s, pid):
    r = s.post(f"{API}/profiles/{pid}/export/ecu")
    assert r.status_code == 200
    art = r.json()
    assert art["deep_link"] is None
    pl = art["payload"]
    assert "fuel_map_ms" in pl and "ignition_map_deg" in pl


def test_inspector_audit_includes_metadata(s, pid):
    r = s.post(f"{API}/profiles/{pid}/inspector/audit").json()
    rid = r["report_id"]
    g = s.get(f"{API}/inspector/reports/{rid}").json()
    assert "engine_metadata" in g
    assert "safety_envelope" in g


# === AI EXPLAINER SSE =======================================================

SAMPLE_FINDING = {
    "code": "FUEL_SUB_MS_PW",
    "severity": "warning",
    "subsystem": "fuel",
    "message": "Several high-load fuel cells fall below the injector minimum pulse width.",
    "remediation": "Increase injector size or reduce target afr in these cells.",
    "cells": [[12, 12], [13, 13], [14, 14]],
}


def _parse_sse(text):
    frames = []
    for raw in text.split("\n\n"):
        if not raw.strip():
            continue
        ev = None
        data_lines = []
        for line in raw.splitlines():
            if line.startswith("event:"):
                ev = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].lstrip())
        frames.append((ev, "\n".join(data_lines)))
    return frames


def test_explain_finding_streams(s):
    body = {
        "finding": SAMPLE_FINDING,
        "profile_name": "TEST_R3_Aggressive",
        "engine_metadata": AGGR_INTAKE,
        "safety_envelope": {
            "afr_min": 10.5, "afr_max": 14.7,
            "ignition_ceiling": 28, "boost_ceiling_kpa": 180,
            "knock_sensitivity": "high", "thermal_risk": "elevated", "warnings": [],
        },
    }
    r = requests.post(f"{API}/inspector/findings/explain", json=body,
                      stream=True, timeout=60)
    assert r.status_code == 200, r.text
    assert "text/event-stream" in r.headers.get("content-type", "")
    raw = r.content.decode("utf-8", errors="replace")
    frames = _parse_sse(raw)
    assert len(frames) >= 3, f"expected multi-frame SSE, got {len(frames)}"
    assert frames[0][0] == "meta", f"first frame should be meta, got {frames[0]}"
    assert "claude-sonnet-4-6" in frames[0][1]
    token_frames = [d for ev, d in frames if ev == "token"]
    assert len(token_frames) >= 2, f"expected multiple token frames, got {len(token_frames)}"
    assert frames[-1][0] == "done"
    text = "".join(t.replace("\\n", "\n") for t in token_frames)
    assert len(text) >= 100, f"explanation too short ({len(text)} chars): {text!r}"


def test_explain_finding_missing_field_returns_422(s):
    r = s.post(f"{API}/inspector/findings/explain", json={"profile_name": "x"})
    assert r.status_code == 422


def test_emergent_llm_key_present_in_env():
    p = "/app/backend/.env"
    assert os.path.exists(p)
    with open(p) as fh:
        assert "EMERGENT_LLM_KEY=" in fh.read()


def test_explain_endpoint_503_path_in_code():
    """Static check: endpoint contains the 503 fallback for missing key.

    Round 5: explainer code was extracted to /app/backend/explainer.py. We now
    accept the 503-path appearing in either server.py or explainer.py.
    """
    paths = ["/app/backend/server.py", "/app/backend/explainer.py"]
    src = ""
    for p in paths:
        if os.path.exists(p):
            with open(p) as fh:
                src += fh.read()
    assert 'EMERGENT_LLM_KEY' in src
    assert '503' in src and 'EMERGENT_LLM_KEY not configured' in src


# === Regression: profile create/list/regenerate/revert/compare ==============

def test_regression_profile_lifecycle(s):
    pkg = s.post(f"{API}/starter-tune/generate", json={"intake": AGGR_INTAKE}).json()
    pr = s.post(f"{API}/profiles", json={
        "name": "TEST_R3_Lifecycle", "intake": AGGR_INTAKE, "tune_package": pkg,
    }).json()
    pid_l = pr["id"]
    try:
        lst = s.get(f"{API}/profiles")
        assert lst.status_code == 200
        assert any(p["id"] == pid_l for p in lst.json())
        rg = s.post(f"{API}/profiles/{pid_l}/regenerate", json={
            "intake": AGGR_INTAKE,
            "adjustments": {"afr_bias": -0.3, "timing_bias": 0.2,
                            "boost_intent": 0.2, "drivability_bias": 0.0},
            "note": "TEST",
        })
        assert rg.status_code == 200
        prof = s.get(f"{API}/profiles/{pid_l}").json()
        assert len(prof["history"]) >= 2
        # revert to gen 0
        rv = s.post(f"{API}/profiles/{pid_l}/revert/0")
        assert rv.status_code == 200
        # compare two generations
        cmp_ = s.get(f"{API}/profiles/{pid_l}/compare/0/1")
        assert cmp_.status_code == 200
    finally:
        s.delete(f"{API}/profiles/{pid_l}")
