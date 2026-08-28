#!/usr/bin/env python3
"""
TwinStock AI - One-Command Local Development Launcher
Runs Backend (port 8000), ML Service (port 8001), and Frontend Proxy (port 8080) simultaneously.
Automatically frees ports before launching.
"""

import os
import sys
import subprocess
import time
import signal

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
ML_DIR = os.path.join(ROOT_DIR, "ml-service")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

processes = []

def free_port(port):
    """Automatically kill any process occupying the target port."""
    if sys.platform == "win32":
        try:
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid != "0" and pid != str(os.getpid()):
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    else:
        try:
            output = subprocess.check_output(f"lsof -t -i:{port}", shell=True).decode()
            for pid in output.strip().splitlines():
                subprocess.run(f"kill -9 {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def cleanup(sig=None, frame=None):
    print("\n[TwinStock AI] Stopping all services...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    print("==========================================================")
    print("           📦 TwinStock AI - Multi-Service System          ")
    print("==========================================================")

    # Clean up any zombie processes occupying our ports
    print("[0/3] Checking and clearing ports 8000, 8001, 8080...")
    for port in [8000, 8001, 8080]:
        free_port(port)
    time.sleep(1)

    # 1. Start ML Forecasting Service (port 8001)
    print("[1/3] Starting ML Forecasting Service on http://127.0.0.1:8001 ...")
    ml_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=ML_DIR
    )
    processes.append(ml_proc)
    time.sleep(1.5)

    # 2. Start Backend FastAPI (port 8000)
    print("[2/3] Starting Backend API Service on http://127.0.0.1:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR
    )
    processes.append(backend_proc)
    time.sleep(1.5)

    # 3. Start Frontend Dev Proxy Server (port 8080)
    print("[3/3] Starting Frontend Web Server on http://127.0.0.1:8080 ...")
    frontend_proc = subprocess.Popen(
        [sys.executable, "dev_server.py"],
        cwd=FRONTEND_DIR
    )
    processes.append(frontend_proc)

    print("\n==========================================================")
    print("🚀 All TwinStock AI services are running!")
    print("   • Frontend Dashboard : http://127.0.0.1:8080/index.html")
    print("   • Manager Dashboard  : http://127.0.0.1:8080/manager.html")
    print("   • Worker Dashboard   : http://127.0.0.1:8080/worker.html")
    print("   • Backend API Docs   : http://127.0.0.1:8000/docs")
    print("   • ML Forecast Health : http://127.0.0.1:8001/health")
    print("==========================================================")
    print("Press Ctrl+C to stop all services.\n")

    try:
        while True:
            time.sleep(2)
            for name, proc in [("ML Service", ml_proc), ("Backend", backend_proc), ("Frontend", frontend_proc)]:
                if proc.poll() is not None:
                    print(f"[Warning] {name} process exited with code {proc.returncode}")
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
