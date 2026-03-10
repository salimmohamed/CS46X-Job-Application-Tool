#!/usr/bin/env python3
"""
Upload flow test: clear profile, upload sample resume, verify response matches resume content.

Run from backend/: python run_upload_test.py [--loop N]
Requires: OPENAI_API_KEY
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

# Load .env if present
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

API_URL = "http://127.0.0.1:8000"
# Markers that must NOT appear when we upload sample_resume.pdf (Alex Johnson)
STALE_MARKERS = [
    "Starratt", "gareth.starratt", "360-903-9606", "garethstarratt.framer",
    "Daimler Autonomous",
]
EXPECTED_MARKERS = ["Alex", "Johnson", "alex.johnson@example.com", "TechNova", "DataEdge", "Berkeley"]


def flatten(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from flatten(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from flatten(v)
    else:
        yield str(obj)


def contains_any(data, markers):
    flat = " ".join(flatten(data)).lower()
    return any(m.lower() in flat for m in markers)


def run_one_test():
    """Run a single test iteration. Returns True on success, False on failure."""
    backend_dir = Path(__file__).parent
    sample_pdf = backend_dir / "tests" / "fixtures" / "sample_resume.pdf"
    if not sample_pdf.exists():
        print(f"ERROR: {sample_pdf} not found. Run: python tests/fixtures/make_sample_resume_pdf.py")
        return False

    # Start server in background
    print("Starting backend server...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "resume_parser:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(backend_dir),
        env={**os.environ, "PYTHONPATH": str(backend_dir)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(30):
            try:
                r = requests.get(f"{API_URL}/profile", timeout=2)
                if r.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)
        else:
            print("ERROR: Server did not start in time")
            return False

        print("Server ready. Clearing profile...")
        r = requests.post(f"{API_URL}/profile/clear", timeout=10)
        if r.status_code != 200:
            print(f"ERROR: Clear failed: {r.text}")
            return False

        # Verify no Gareth after clear
        r = requests.get(f"{API_URL}/profile", timeout=5)
        data = r.json()
        if contains_any(data.get("applicant_info", {}), STALE_MARKERS):
            print("WARNING: Profile still has stale data after clear. Continuing anyway.")

        print("Uploading sample_resume.pdf (Alex Johnson)...")
        with open(sample_pdf, "rb") as f:
            r = requests.post(
                f"{API_URL}/upload",
                files={"file": ("sample_resume.pdf", f, "application/pdf")},
                timeout=60,
            )

        if r.status_code != 200:
            print(f"ERROR: Upload failed {r.status_code}: {r.text[:500]}")
            return False

        data = r.json()
        applicant = data.get("applicant_info", data)

        if contains_any(applicant, STALE_MARKERS):
            print("FAIL: Upload response contains stale/cached data!")
            print(json.dumps(applicant, indent=2)[:800])
            return False

        if not contains_any(applicant, EXPECTED_MARKERS):
            print("FAIL: Upload response missing expected resume data!")
            print(json.dumps(applicant, indent=2)[:800])
            return False

        print("PASS: Upload returns resume data only.")

        r = requests.get(f"{API_URL}/profile", timeout=5)
        profile = r.json()
        if contains_any(profile.get("applicant_info", {}), STALE_MARKERS):
            print("FAIL: GET /profile contains stale data!")
            return False
        print("PASS: GET /profile has correct data.")

        # Check profile.json on disk
        profile_path = backend_dir / "profile.json"
        if profile_path.exists():
            disk = json.loads(profile_path.read_text())
            if contains_any(disk.get("applicant_info", {}), STALE_MARKERS):
                print("FAIL: profile.json contains stale data!")
                return False
        print("PASS: profile.json on disk has correct data.")

        print("\nAll checks passed. Upload flow works correctly.")
        return True
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description="Test upload flow")
    parser.add_argument("--loop", type=int, default=1, help="Run test N times")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. Set it in .env or environment.")
        sys.exit(1)

    for i in range(args.loop):
        if args.loop > 1:
            print(f"\n=== Run {i + 1}/{args.loop} ===")
        if not run_one_test():
            sys.exit(1)

    if args.loop > 1:
        print(f"\nAll {args.loop} runs passed.")


if __name__ == "__main__":
    main()
