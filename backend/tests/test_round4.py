"""Round 4 backend tests — explain cache (LRU + key isolation + stats/clear) + SSE heartbeat ping."""
import os
import time
import copy
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


SAMPLE_BODY = {
    "finding": {
        "code": "FUEL_SUB_MS_PW",
        "severity": "warning",
        "subsystem": "fuel",
        "message": "test",
        "remediation": "test",
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


# --- SSE parsing helper -----------------------------------------------------

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


def _stream_explain(body, timeout=90):
    t0 = time.time()
    r = requests.post(f"{API}/inspector/findings/explain",
                      json=body, stream=True, timeout=timeout)
    assert r.status_code == 200, r.text
    raw = r.content.decode("utf-8", errors="replace")
    elapsed = time.time() - t0
    return raw, _parse_sse(raw), elapsed


# --- Setup: clear cache once before this module's tests --------------------

@pytest.fixture(scope="module", autouse=True)
def _clear_cache_module():
    requests.delete(f"{API}/inspector/explain-cache")
    yield
    requests.delete(f"{API}/inspector/explain-cache")


# === CACHE TESTS ===========================================================

def test_first_call_is_uncached_and_slow():
    raw, frames, elapsed = _stream_explain(SAMPLE_BODY)
    assert frames[0][0] == "meta"
    assert '"cached":false' in frames[0][1] or "'cached':false" in frames[0][1]
    assert elapsed > 1.0, f"live LLM call too fast ({elapsed:.2f}s) — was it cached?"
    tokens = [d for ev, d in frames if ev == "token"]
    assert len(tokens) >= 4
    assert frames[-1][0] == "done"


def test_second_call_is_cached_and_fast_with_identical_text():
    # First call to populate cache
    raw1, frames1, _ = _stream_explain(SAMPLE_BODY)
    text1 = "".join(d.replace("\\n", "\n") for ev, d in frames1 if ev == "token")
    assert text1.strip(), "empty first response — cannot validate cache equality"

    # Second identical call should be cached + fast
    raw2, frames2, elapsed2 = _stream_explain(SAMPLE_BODY)
    assert frames2[0][0] == "meta"
    assert '"cached":true' in frames2[0][1]
    assert elapsed2 < 2.0, f"cache hit too slow ({elapsed2:.2f}s)"

    text2 = "".join(d.replace("\\n", "\n") for ev, d in frames2 if ev == "token")
    assert text1.strip() == text2.strip(), "cached text differs from original"


def test_cache_key_isolation_different_metadata():
    # Ensure first body is cached
    _stream_explain(SAMPLE_BODY)
    # Now change engine_metadata
    body2 = copy.deepcopy(SAMPLE_BODY)
    body2["engine_metadata"]["target_hp"] = 600  # different field
    raw, frames, elapsed = _stream_explain(body2)
    assert frames[0][0] == "meta"
    assert '"cached":false' in frames[0][1], \
        f"expected cached:false for different metadata, got: {frames[0][1]}"
    assert elapsed > 1.0


def test_cache_stats_endpoint_reports_entries():
    stats = requests.get(f"{API}/inspector/explain-cache/stats").json()
    assert "entries" in stats and "max" in stats
    assert stats["max"] == 64
    assert stats["entries"] >= 2, f"expected >=2 entries, got {stats}"


def test_cache_clear_resets_entries():
    pre_stats = requests.get(f"{API}/inspector/explain-cache/stats").json()
    pre_n = pre_stats["entries"]
    clr = requests.delete(f"{API}/inspector/explain-cache").json()
    assert clr.get("cleared") == pre_n, f"clear count mismatch: {clr} vs {pre_n}"
    post = requests.get(f"{API}/inspector/explain-cache/stats").json()
    assert post["entries"] == 0
    # Re-calling should be live again
    _, frames, elapsed = _stream_explain(SAMPLE_BODY)
    assert '"cached":false' in frames[0][1]
    assert elapsed > 1.0


# === HEARTBEAT PING ========================================================

def test_heartbeat_ping_emitted_during_live_stream():
    # Ensure live (not cached) call
    requests.delete(f"{API}/inspector/explain-cache")
    raw, frames, elapsed = _stream_explain(SAMPLE_BODY)
    assert '"cached":false' in frames[0][1]
    pings = [d for ev, d in frames if ev == "ping"]
    tokens = [d for ev, d in frames if ev == "token"]
    # We expect at least 1 ping for a 4-6 sentence response (>=8 tokens)
    assert len(tokens) >= 8, \
        f"need >=8 tokens to assert >=1 ping, got {len(tokens)}"
    assert len(pings) >= 1, \
        f"no ping heartbeat frame found; tokens={len(tokens)}, frames={len(frames)}"
