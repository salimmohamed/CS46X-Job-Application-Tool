"""
Upload flow test: verifies upload returns data from the uploaded resume only.

Run from backend/: pytest tests/test_upload_flow.py -v -s
Requires: OPENAI_API_KEY, sample_resume.pdf
"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Must NOT appear when we upload sample_resume.pdf (Alex Johnson)
STALE_MARKERS = [
    "Starratt", "gareth.starratt@gmail.com", "360-903-9606",
    "garethstarratt.framer.media", "Daimler Autonomous",
]

EXPECTED_MARKERS = [
    "Alex",
    "Johnson",
    "alex.johnson@example.com",
    "TechNova",
    "DataEdge",
    "Berkeley",
]


def _flatten(obj, prefix=""):
    """Flatten nested dict to string for searching."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield str(obj)


def _contains_any(data, markers):
    """Check if flattened data contains any of the markers."""
    flat = " ".join(_flatten(data)).lower()
    return any(m.lower() in flat for m in markers)


def _ensure_profile_cleared(client: TestClient):
    """Clear profile and verify no stale data."""
    r = client.post("/profile/clear")
    assert r.status_code == 200, f"Clear failed: {r.text}"
    r2 = client.get("/profile")
    assert r2.status_code == 200
    data = r2.json()
    applicant = data.get("applicant_info", {})
    assert not _contains_any(applicant, STALE_MARKERS), "Profile still has stale data after clear"


@pytest.fixture
def client():
    """Create TestClient. Skips if OPENAI_API_KEY not set."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    # Import here so we don't fail if key is missing at import time
    # Run from backend/ so: cd backend && pytest tests/test_upload_flow.py -v -s
    import sys
    backend_dir = Path(__file__).resolve().parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from resume_parser import app
    return TestClient(app)


@pytest.fixture
def sample_pdf_path():
    p = Path(__file__).parent / "fixtures" / "sample_resume.pdf"
    if not p.exists():
        pytest.skip(f"sample_resume.pdf not found at {p}. Run: python backend/tests/fixtures/make_sample_resume_pdf.py")
    return p


def test_upload_returns_only_resume_data_not_cached(client, sample_pdf_path):
    """Upload sample resume; verify response has expected data and no stale data."""
    _ensure_profile_cleared(client)

    with open(sample_pdf_path, "rb") as f:
        r = client.post("/upload", files={"file": ("sample_resume.pdf", f, "application/pdf")})

    assert r.status_code == 200, f"Upload failed: {r.text}"
    data = r.json()
    applicant = data.get("applicant_info", data)

    assert not _contains_any(applicant, STALE_MARKERS), (
        f"Upload response contains stale data: {json.dumps(applicant, indent=2)[:500]}"
    )
    assert _contains_any(applicant, EXPECTED_MARKERS), (
        f"Upload response missing Alex Johnson data from resume. Got: {json.dumps(applicant, indent=2)[:500]}"
    )


def test_profile_json_after_upload_has_resume_data_not_cached(client, sample_pdf_path):
    """After upload, GET /profile and profile.json must have resume data only."""
    _ensure_profile_cleared(client)

    with open(sample_pdf_path, "rb") as f:
        r = client.post("/upload", files={"file": ("sample_resume.pdf", f, "application/pdf")})
    assert r.status_code == 200

    # GET /profile
    r2 = client.get("/profile")
    assert r2.status_code == 200
    profile = r2.json()
    applicant = profile.get("applicant_info", {})

    assert not _contains_any(applicant, STALE_MARKERS), (
        f"GET /profile contains stale data: {json.dumps(applicant, indent=2)[:500]}"
    )
    assert _contains_any(applicant, EXPECTED_MARKERS), (
        f"GET /profile missing Alex data. Got: {json.dumps(applicant, indent=2)[:500]}"
    )

    # profile.json on disk
    backend_dir = Path(__file__).resolve().parent.parent
    profile_path = backend_dir / "profile.json"
    if profile_path.exists():
        with open(profile_path, encoding="utf-8") as pf:
            disk = json.load(pf)
        disk_applicant = disk.get("applicant_info", {})
        assert not _contains_any(disk_applicant, STALE_MARKERS), (
            f"profile.json contains stale data: {json.dumps(disk_applicant, indent=2)[:500]}"
        )
