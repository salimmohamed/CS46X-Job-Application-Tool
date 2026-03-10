#!/usr/bin/env python3
"""
One-shot runner for the Job Application Tool demo.
Starts the backend API and frontend dev server, then opens the app in the browser.

Usage (from project root):
  python run_demo.py

Requires:
  - Backend: pip install -r backend/requirements.txt (from project root or backend)
  - Frontend: npm install in frontend/ (done automatically if node_modules missing)
"""
import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent


def _load_backend_env() -> None:
    """Load backend/.env into os.environ so the backend process gets OPENAI_API_KEY etc."""
    env_file = PROJECT_ROOT / "backend" / ".env"
    if not env_file.exists():
        return
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)


BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173
APP_URL = f"http://localhost:{FRONTEND_PORT}"

processes: List[subprocess.Popen] = []


def _kill_process_on_port(port: int) -> bool:
    """Kill any process listening on the given port. Returns True if something was killed."""
    killed = False
    if sys.platform == "win32":
        try:
            out = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=PROJECT_ROOT,
            )
            for line in (out.stdout or "").splitlines():
                if f":{port}" in line and "LISTENING" in line.upper():
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit():
                            subprocess.run(
                                ["taskkill", "/PID", pid, "/F"],
                                capture_output=True,
                                timeout=5,
                            )
                            killed = True
                            break
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout and result.stdout.strip():
                for pid in result.stdout.strip().split():
                    if pid.isdigit():
                        subprocess.run(["kill", "-9", pid], capture_output=True, timeout=5)
                        killed = True
        except Exception:
            pass
    return killed


def _free_ports_for_restart() -> None:
    """Kill any existing backend/frontend processes on our ports so we can start fresh."""
    ports_to_free = [BACKEND_PORT, FRONTEND_PORT, 5174, 5175]
    any_killed = False
    for port in ports_to_free:
        if _kill_process_on_port(port):
            print(f"Freed port {port} (stopped previous process).")
            any_killed = True
            time.sleep(0.5)
    if any_killed:
        time.sleep(1)


def main() -> int:
    if not BACKEND_DIR.is_dir():
        print("Error: backend/ not found. Run from project root.")
        return 1
    if not FRONTEND_DIR.is_dir():
        print("Error: frontend/ not found. Run from project root.")
        return 1

    def cleanup() -> None:
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    def on_signal(_sig: int, _frame: object) -> None:
        print("\nShutting down...")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_signal)

    _load_backend_env()

    print("Checking for existing servers on ports 8000, 5173...")
    _free_ports_for_restart()

    # Ensure frontend deps
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.is_dir():
        print("Installing frontend dependencies (npm install)...")
        subprocess.run(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            shell=os.name == "nt",
            check=True,
        )

    # Start backend
    print("Starting backend (uvicorn resume_parser:app)...")
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "resume_parser:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(BACKEND_PORT),
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(BACKEND_DIR))
    if str(BACKEND_DIR) not in env.get("PYTHONPATH", ""):
        env["PYTHONPATH"] = str(BACKEND_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=BACKEND_DIR,
        env=env,
        stdout=None,
        stderr=None,
    )
    processes.append(backend_proc)

    # Start frontend
    print("Starting frontend (npm run dev)...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        shell=os.name == "nt",
        stdout=None,
        stderr=None,
    )
    processes.append(frontend_proc)

    # Wait for servers to be up
    print("Waiting for servers to start...")
    time.sleep(3)

    if backend_proc.poll() is not None:
        print("Backend exited early. Check backend/requirements.txt and OPENAI_API_KEY.")
        cleanup()
        return 1
    if frontend_proc.poll() is not None:
        print("Frontend exited early. Check frontend (npm install).")
        cleanup()
        return 1

    # Open browser
    try:
        import webbrowser
        webbrowser.open(APP_URL)
        print(f"Opened {APP_URL}")
    except Exception as e:
        print(f"Could not open browser: {e}")
        print(f"Open manually: {APP_URL}")

    print("\nDemo is running. Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("Backend process exited.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend process exited.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
