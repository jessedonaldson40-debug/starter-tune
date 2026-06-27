"""Round 5 — regression coverage for explainer module refactor.

The behavioural contract should be unchanged: same SSE event sequence, same
cache semantics, same CRUD on /explain-cache. Tests are read-only against the
live backend except for the cache DELETE used to set up cold-cache state.
"""
from __future__ import annotations

import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://starter-tune-gen.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SAMPLE = {
    "finding": {
        "code": "FUEL_SUB_MS_PW",
        "severity": "warning",
        "subsystem": "fuel",
        "message": "Round5 test",
        "remediation": "x",
    },
    "profile_name": "X",
    "engine_metadata": {
        "displacement_l": 2.0,
        "cylinders": 4,
        "induction": "Turbo",
        "fuel_type": "93",
        "target_hp": 350,
        "rev_limit": 7000,
        "injector_cc": 650,
        "compression_ratio": 9.5,
    },
    "safety_envelope": {
        "afr_min": 11.5,
        "afr_max": 15.0,
        "ignition_ceiling": 24,
        "boost_ceiling_kpa": 180,
        "knock_sensitivity": "moderate",
        "thermal_risk": "moderate",
    },
}


def _parse_sse(text: str):
    """Return list of (event, data) tuples in order."""
    events = []
    current_event = None
    for line in text.splitlines():
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
            if current_event is not None:
                events.append((current_event, data))
                current_event = None
        elif line == "":
            current_event = None
    return events


@pytest.fixture(scope="module")
def cold_cache():
    """Clear the cache so the first 'first call' test sees cold."""
    r = requests.delete(f"{API}/inspector/explain-cache", timeout=10)
    assert r.status_code == 200
    return r.json()


# === Cache management endpoints =============================================

def test_cache_stats_after_clear(cold_cache):
    r = requests.get(f"{API}/inspector/explain-cache/stats", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["max"] == 64
    assert body["entries"] == 0


# === Cold call: meta cached:false, token frames, ping, terminal done ========

def test_cold_call_streams_full_sse_contract(cold_cache):
    with requests.post(
        f"{API}/inspector/findings/explain",
        json=SAMPLE,
        stream=True,
        timeout=90,
    ) as r:
        assert r.status_code == 200
        body = r.text  # consume

    events = _parse_sse(body)
    assert len(events) > 0
    # meta is first
    assert events[0][0] == "meta"
    assert '"cached":false' in events[0][1]
    assert "claude-sonnet-4-6" in events[0][1]
    # at least one token, at least one ping, terminal done
    kinds = [e[0] for e in events]
    assert kinds.count("token") >= 1, kinds
    assert kinds.count("ping") >= 1, kinds
    assert kinds[-1] == "done"
    # aggregate text >= 100 chars
    aggregated = "".join(d.replace("\\n", "\n") for k, d in events if k == "token")
    assert len(aggregated) >= 100, f"aggregated len={len(aggregated)}"


# === Warm call: identical body cached:true, fast, byte-for-byte =============

def test_warm_call_cached_replay_matches():
    # First call (may already be cached from previous test — that's fine)
    with requests.post(f"{API}/inspector/findings/explain", json=SAMPLE, stream=True, timeout=90) as r1:
        body1 = r1.text
    events1 = _parse_sse(body1)
    agg1 = "".join(d.replace("\\n", "\n") for k, d in events1 if k == "token")

    # Second call should be cached
    t0 = time.time()
    with requests.post(f"{API}/inspector/findings/explain", json=SAMPLE, stream=True, timeout=30) as r2:
        body2 = r2.text
    elapsed = time.time() - t0

    events2 = _parse_sse(body2)
    assert events2[0][0] == "meta"
    assert '"cached":true' in events2[0][1]
    assert elapsed < 5.0, f"cached replay took {elapsed:.2f}s"
    agg2 = "".join(d.replace("\\n", "\n") for k, d in events2 if k == "token")
    assert agg1 == agg2, "cached aggregated text differs from first call"


# === Different engine_metadata produces a different cache key ===============

def test_different_engine_metadata_is_cold():
    alt = dict(SAMPLE)
    alt["engine_metadata"] = dict(SAMPLE["engine_metadata"], displacement_l=3.0, target_hp=500)
    with requests.post(f"{API}/inspector/findings/explain", json=alt, stream=True, timeout=90) as r:
        body = r.text
    events = _parse_sse(body)
    assert events[0][0] == "meta"
    assert '"cached":false' in events[0][1]


# === Stats reflect entries after cold calls =================================

def test_stats_has_entries_after_cold_calls():
    r = requests.get(f"{API}/inspector/explain-cache/stats", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["max"] == 64
    assert body["entries"] >= 1


# === DELETE clears and returns count ========================================

def test_delete_clears_and_zeroes_stats():
    r = requests.delete(f"{API}/inspector/explain-cache", timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json().get("cleared"), int)
    stats = requests.get(f"{API}/inspector/explain-cache/stats", timeout=10).json()
    assert stats["entries"] == 0


# === Malformed body returns 422 =============================================

def test_missing_finding_returns_422():
    r = requests.post(f"{API}/inspector/findings/explain", json={"profile_name": "X"}, timeout=10)
    assert r.status_code == 422
