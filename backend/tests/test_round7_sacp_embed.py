"""Round 7 — SACP embedded last_sessions / last_reports tests.

Covers:
- GET /api/packages/{id} returns simulation.last_sessions + inspector.last_reports
  with required fields (and excludes bulky 'samples'/'findings').
- Sorted by created_at desc, capped at 5 entries each.
- Empty lists (not null) when no sessions/reports exist for a profile.
- GET /api/packages/{id}/download body still parses JSON, contains the embedded
  lists, and X-SACP-Checksum header matches package_metadata.checksum after the
  re-stamp.
- Round-trip via download → upload still works (no regression).
"""
import os
import json
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

INTAKE = {
    "displacement_l": 2.0,
    "cylinders": 4,
    "induction": "Turbo",
    "fuel_type": "93",
    "target_hp": 350,
    "rev_limit": 7200,
    "injector_cc": 550,
    "compression_ratio": 9.5,
    "intercooler_class": "Front Mount",
    "spool_rpm": 3200,
    "intended_use": "street",
}

SCENARIOS = [
    "idle_warm",
    "cold_start",
    "wot_pull",
    "knock_event",
    "lean_cruise",
    "rich_cruise",
]


def _create_profile(name):
    pkg = requests.post(f"{API}/starter-tune/generate", json={"intake": INTAKE}).json()
    r = requests.post(f"{API}/profiles", json={
        "name": name, "intake": INTAKE, "tune_package": pkg,
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def seed_with_history():
    pid = _create_profile("TEST_R7_EMBED")
    # run 6 diagsim sessions (so we can confirm the cap at 5)
    created_sessions = []
    for i, scenario in enumerate(SCENARIOS):
        r = requests.post(
            f"{API}/profiles/{pid}/diagsim/run",
            json={"scenario": scenario, "seed": 1000 + i},
        )
        assert r.status_code == 200, r.text
        created_sessions.append(r.json())
        # ensure created_at order is monotonically increasing (ISO timestamps)
        time.sleep(0.05)
    # run 6 inspector audits to test cap at 5
    created_reports = []
    for _ in range(6):
        r = requests.post(f"{API}/profiles/{pid}/inspector/audit")
        assert r.status_code == 200, r.text
        created_reports.append(r.json())
        time.sleep(0.05)
    yield pid, created_sessions, created_reports
    requests.delete(f"{API}/packages/{pid}")


@pytest.fixture(scope="module")
def fresh_profile():
    pid = _create_profile("TEST_R7_FRESH")
    yield pid
    requests.delete(f"{API}/packages/{pid}")


# ───────────────────────── GET /api/packages/{id} ─────────────────────────

def test_get_package_embeds_last_sessions(seed_with_history):
    pid, sessions_in, _ = seed_with_history
    pkg = requests.get(f"{API}/packages/{pid}").json()

    last_sessions = pkg.get("simulation", {}).get("last_sessions")
    assert isinstance(last_sessions, list), f"last_sessions not list: {last_sessions!r}"
    assert len(last_sessions) >= 1
    assert len(last_sessions) <= 5, f"expected <=5 sessions, got {len(last_sessions)}"

    REQUIRED = {"session_id", "scenario", "scenario_name", "created_at",
                "summary", "fault_codes", "source_generation_index"}
    for entry in last_sessions:
        missing = REQUIRED - set(entry.keys())
        assert not missing, f"session missing fields {missing}: {entry}"
        # bulky samples must NOT be embedded
        assert "samples" not in entry, f"samples leaked into session embed: {entry.keys()}"


def test_get_package_embeds_last_reports(seed_with_history):
    pid, _, _ = seed_with_history
    pkg = requests.get(f"{API}/packages/{pid}").json()

    last_reports = pkg.get("inspector", {}).get("last_reports")
    assert isinstance(last_reports, list)
    assert len(last_reports) >= 1
    assert len(last_reports) <= 5

    REQUIRED = {"report_id", "created_at", "score", "subsystem_scores",
                "counts", "recommendations", "source_generation_index"}
    for entry in last_reports:
        missing = REQUIRED - set(entry.keys())
        assert not missing, f"report missing fields {missing}: {entry}"
        assert "findings" not in entry, f"findings leaked: {entry.keys()}"
        assert len(entry["recommendations"]) <= 5


def test_embedded_lists_sorted_desc_by_created_at(seed_with_history):
    pid, _, _ = seed_with_history
    pkg = requests.get(f"{API}/packages/{pid}").json()

    sessions = pkg["simulation"]["last_sessions"]
    timestamps = [s["created_at"] for s in sessions]
    assert timestamps == sorted(timestamps, reverse=True), \
        f"sessions not sorted desc: {timestamps}"

    reports = pkg["inspector"]["last_reports"]
    rtimestamps = [r["created_at"] for r in reports]
    assert rtimestamps == sorted(rtimestamps, reverse=True), \
        f"reports not sorted desc: {rtimestamps}"


def test_embedded_lists_capped_at_5(seed_with_history):
    # We created 6 sessions and 6 audits. Cap is 5 each.
    pid, _, _ = seed_with_history
    pkg = requests.get(f"{API}/packages/{pid}").json()
    assert len(pkg["simulation"]["last_sessions"]) == 5
    assert len(pkg["inspector"]["last_reports"]) == 5


# ───────────────────────── No sessions / no reports ─────────────────────────

def test_get_package_empty_lists_when_no_history(fresh_profile):
    pid = fresh_profile
    pkg = requests.get(f"{API}/packages/{pid}").json()
    assert pkg["simulation"]["last_sessions"] == []
    assert pkg["inspector"]["last_reports"] == []


# ───────────────────────── GET /api/packages/{id}/download ─────────────────────────

def test_download_includes_embedded_refs_and_checksum_matches(seed_with_history):
    pid, _, _ = seed_with_history
    r = requests.get(f"{API}/packages/{pid}/download")
    assert r.status_code == 200, r.text
    # Header checksum
    header_checksum = r.headers.get("X-SACP-Checksum")
    assert header_checksum, "Missing X-SACP-Checksum header"

    body = json.loads(r.text)
    # Embedded refs present in downloaded body
    assert len(body["simulation"]["last_sessions"]) >= 1
    assert len(body["inspector"]["last_reports"]) >= 1
    # Each session entry still excludes 'samples'
    for s in body["simulation"]["last_sessions"]:
        assert "samples" not in s
    for rep in body["inspector"]["last_reports"]:
        assert "findings" not in rep

    # Checksum re-stamped: header must equal package_metadata.checksum in body
    body_checksum = body["package_metadata"]["checksum"]
    assert header_checksum == body_checksum, \
        f"header checksum {header_checksum} != body {body_checksum}"


def test_download_then_upload_round_trip_still_works(seed_with_history):
    pid, _, _ = seed_with_history
    r = requests.get(f"{API}/packages/{pid}/download")
    assert r.status_code == 200
    body = r.text  # raw JSON (str)
    up = requests.post(
        f"{API}/packages/upload",
        data=body,
        headers={"Content-Type": "application/x-sacp+json"},
    )
    assert up.status_code == 200, up.text
    new_id = up.json()["package_metadata"]["package_id"]
    try:
        # The new profile should be retrievable as a package
        new_pkg = requests.get(f"{API}/packages/{new_id}").json()
        assert new_pkg["package_metadata"]["name"]  # has a name
        # On a freshly-imported profile, no sessions/reports yet → empty lists
        assert new_pkg["simulation"]["last_sessions"] == []
        assert new_pkg["inspector"]["last_reports"] == []
    finally:
        requests.delete(f"{API}/packages/{new_id}")
