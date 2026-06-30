"""Round 6 — STANDAILONE Calibration Package (SACP) v1.0.0 tests."""
import os
import re
import json
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

REQUIRED_SECTIONS = [
    "package_metadata", "vehicle", "engine", "hardware", "calibration",
    "safety_envelope", "telemetry_assumptions", "generation_metadata",
    "confidence", "warnings", "simulation", "inspector",
    "compare_history", "exports", "notes",
]


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


def _create_profile(name="TEST_R6_SACP", intake=None):
    intake = intake or INTAKE
    pkg = requests.post(f"{API}/starter-tune/generate", json={"intake": intake}).json()
    r = requests.post(f"{API}/profiles", json={
        "name": name, "intake": intake, "tune_package": pkg,
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def seed_profile():
    pid = _create_profile()
    yield pid
    requests.delete(f"{API}/packages/{pid}")


# ---------------- SCHEMA ----------------
def test_schema_endpoint():
    r = requests.get(f"{API}/packages/schema")
    assert r.status_code == 200
    data = r.json()
    assert data["schema_version"] == "1.0.0"
    assert ".sacp" in data["file_extensions"]
    assert ".standalone" in data["file_extensions"]
    keys = [s["key"] for s in data["sections"]]
    assert keys == REQUIRED_SECTIONS
    for s in data["sections"]:
        assert "required" in s and "description" in s


# ---------------- LIST ----------------
def test_list_packages_contains_seed(seed_profile):
    r = requests.get(f"{API}/packages")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    match = [p for p in items if p["package_id"] == seed_profile]
    assert match, "seed not in list"
    item = match[0]
    for k in ("package_id", "name", "created_at", "last_modified_at",
              "schema_version", "displacement_l", "cylinders", "induction",
              "fuel_type", "target_hp", "active_generation_index", "export_count"):
        assert k in item, f"missing {k}"


# ---------------- GET (full SACP) ----------------
def test_get_full_package(seed_profile):
    r = requests.get(f"{API}/packages/{seed_profile}")
    assert r.status_code == 200
    pkg = r.json()
    for s in REQUIRED_SECTIONS:
        assert s in pkg, f"missing section {s}"
    chk = pkg["package_metadata"]["checksum"]
    assert chk and re.fullmatch(r"sha256:[0-9a-f]{32}", chk), f"bad checksum: {chk}"

    fuel = pkg["calibration"]["fuel_table"]["values"]
    assert len(fuel) == 16
    for row in fuel:
        assert len(row) == 16
        for v in row:
            assert isinstance(v, (int, float))

    ve = pkg["calibration"]["ve_curve"]
    assert ve is not None
    assert len(ve["values"]) == 16


# ---------------- DOWNLOAD ----------------
def test_download_headers_and_body(seed_profile):
    r = requests.get(f"{API}/packages/{seed_profile}/download")
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/x-sacp+json")
    cd = r.headers["Content-Disposition"]
    assert "attachment" in cd and ".sacp" in cd
    assert r.headers["X-SACP-Schema-Version"] == "1.0.0"
    chk = r.headers["X-SACP-Checksum"]
    assert re.fullmatch(r"sha256:[0-9a-f]{32}", chk)
    body = json.loads(r.text)
    for s in REQUIRED_SECTIONS:
        assert s in body


# ---------------- UPLOAD ROUND-TRIP ----------------
def test_upload_roundtrip(seed_profile):
    dl = requests.get(f"{API}/packages/{seed_profile}/download")
    body = json.loads(dl.text)
    original_fuel = body["calibration"]["fuel_table"]["values"]

    up = requests.post(f"{API}/packages/upload", json=body)
    assert up.status_code == 200, up.text
    new_pkg = up.json()
    new_id = new_pkg["package_metadata"]["package_id"]
    try:
        assert new_id != seed_profile
        assert new_pkg["package_metadata"]["name"].endswith("(imported)")
        new_fuel = new_pkg["calibration"]["fuel_table"]["values"]
        assert new_fuel == original_fuel

        lst = requests.get(f"{API}/packages").json()
        assert any(p["package_id"] == new_id for p in lst)
    finally:
        requests.delete(f"{API}/packages/{new_id}")


def test_upload_malformed_returns_422():
    bad = {"package_metadata": {"package_id": "x", "created_at": "2024", "last_modified_at": "2024"}}
    r = requests.post(f"{API}/packages/upload", json=bad)
    assert r.status_code == 422


# ---------------- DUPLICATE ----------------
def test_duplicate_package(seed_profile):
    src_pkg = requests.get(f"{API}/packages/{seed_profile}").json()
    src_fuel = src_pkg["calibration"]["fuel_table"]["values"]

    r = requests.post(f"{API}/packages/{seed_profile}/duplicate")
    assert r.status_code == 200, r.text
    dup = r.json()
    new_id = dup["package_metadata"]["package_id"]
    try:
        assert new_id != seed_profile
        assert dup["package_metadata"]["name"].endswith("(copy)")
        assert dup["exports"] == []
        assert dup["calibration"]["fuel_table"]["values"] == src_fuel

        lst = requests.get(f"{API}/packages").json()
        assert any(p["package_id"] == new_id for p in lst)
    finally:
        requests.delete(f"{API}/packages/{new_id}")


# ---------------- RENAME ----------------
def test_rename_package(seed_profile):
    new_name = "TEST_R6_Renamed"
    before = requests.get(f"{API}/packages/{seed_profile}").json()
    r = requests.patch(f"{API}/packages/{seed_profile}/rename", json={"name": new_name})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["package_metadata"]["name"] == new_name
    assert updated["package_metadata"]["last_modified_at"] >= before["package_metadata"]["last_modified_at"]


# ---------------- NOTES ----------------
def test_notes_crud(seed_profile):
    r = requests.post(f"{API}/packages/{seed_profile}/notes",
                       json={"text": "dyno verified", "author": "tuner"})
    assert r.status_code == 200, r.text
    note = r.json()
    assert "note_id" in note
    assert "created_at" in note
    nid = note["note_id"]

    pkg = requests.get(f"{API}/packages/{seed_profile}").json()
    assert any(n.get("note_id") == nid for n in pkg["notes"])

    # Empty text rejected
    bad = requests.post(f"{API}/packages/{seed_profile}/notes",
                         json={"text": "", "author": "tuner"})
    assert bad.status_code == 422

    # Delete
    dl = requests.delete(f"{API}/packages/{seed_profile}/notes/{nid}")
    assert dl.status_code == 200
    pkg2 = requests.get(f"{API}/packages/{seed_profile}").json()
    assert not any(n.get("note_id") == nid for n in pkg2["notes"])


# ---------------- DELETE ----------------
def test_delete_package_cascades_profile():
    pid = _create_profile(name="TEST_R6_DELETE", intake={
        "displacement_l": 1.6, "cylinders": 4, "induction": "NA",
        "fuel_type": "91", "target_hp": 150, "rev_limit": 7000,
        "injector_cc": 320, "compression_ratio": 10.5,
        "intercooler_class": "Stock", "spool_rpm": 0, "intended_use": "street",
    })

    d = requests.delete(f"{API}/packages/{pid}")
    assert d.status_code == 200
    g = requests.get(f"{API}/packages/{pid}")
    assert g.status_code == 404
    gp = requests.get(f"{API}/profiles/{pid}")
    assert gp.status_code == 404
