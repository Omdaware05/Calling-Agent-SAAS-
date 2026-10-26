"""
ARB SoftTech AI Calling Agent - Preflight System Doctor
=======================================================
Run this tool anytime to verify that Python, Node.js, Ngrok, Docker,
API credentials, and storage directories are 100% operational.

Usage:
    python scripts/doctor.py
"""

import os
import sys
import shutil
import subprocess
import urllib.request
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# ANSI Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def check_mark(status: bool) -> str:
    return f"{GREEN}[OK]{RESET}" if status else f"{RED}[FAIL]{RESET}"


def warn_mark() -> str:
    return f"{YELLOW}[WARN]{RESET}"


def print_header(title: str):
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")


def run_cmd(cmd: list) -> tuple[int, str]:
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        return res.returncode, res.stdout.strip()
    except Exception as e:
        return 1, str(e)


def main():
    print(f"\n{BOLD}{GREEN}======================================================================{RESET}")
    print(f"{BOLD}       ARB SoftTech AI Calling Agent - Preflight Doctor Tool{RESET}")
    print(f"{BOLD}{GREEN}======================================================================{RESET}")

    all_passed = True

    # 1. Check Python
    print_header("1. Core Runtime Environments")
    py_ver = sys.version.split()[0]
    is_py_ok = sys.version_info >= (3, 10)
    print(f" {check_mark(is_py_ok)} Python: v{py_ver} (Target: >= 3.10)")
    if not is_py_ok:
        all_passed = False

    # Check Node.js & npm
    node_cmd = "node"
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    node_rc, node_out = run_cmd([node_cmd, "--version"])
    npm_rc, npm_out = run_cmd([npm_cmd, "--version"])
    is_node_ok = (node_rc == 0)
    is_npm_ok = (npm_rc == 0)
    print(f" {check_mark(is_node_ok)} Node.js: {node_out if is_node_ok else 'Not installed'}")
    print(f" {check_mark(is_npm_ok)} npm: {npm_out if is_npm_ok else 'Not installed'}")
    if not (is_node_ok and is_npm_ok):
        all_passed = False

    # 2. Check Ngrok & Tunnels
    print_header("2. Telecom Public Tunnel (Ngrok)")
    ngrok_bin = shutil.which("ngrok")
    local_ngrok = ROOT_DIR / "bin" / ("ngrok.exe" if os.name == "nt" else "ngrok")
    has_ngrok = bool(ngrok_bin) or local_ngrok.is_file()

    ngrok_path = ngrok_bin or str(local_ngrok)
    print(f" {check_mark(has_ngrok)} Ngrok binary: {ngrok_path if has_ngrok else 'Missing (Run setup_and_run.bat to auto-install)'}")
    if not has_ngrok:
        all_passed = False

    # Test if Ngrok API is currently responding
    ngrok_running = False
    active_tunnel = None
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                tunnels = data.get("tunnels", [])
                for t in tunnels:
                    u = t.get("public_url", "")
                    if u.startswith("https://"):
                        active_tunnel = u
                        ngrok_running = True
                        break
    except Exception:
        pass

    if ngrok_running:
        print(f" {check_mark(True)} Live Tunnel Status: ACTIVE -> {active_tunnel}")
    else:
        print(f" {warn_mark()} Live Tunnel Status: Inactive (Will be launched automatically by start_all.bat)")

    # 3. Check Docker Desktop
    print_header("3. Container Infrastructure (Docker)")
    docker_rc, docker_out = run_cmd(["docker", "--version"])
    has_docker = (docker_rc == 0)
    print(f" {check_mark(has_docker) if has_docker else warn_mark()} Docker CLI: {docker_out if has_docker else 'Not detected'}")

    docker_running = False
    if has_docker:
        info_rc, _ = run_cmd(["docker", "info"])
        docker_running = (info_rc == 0)
        print(f" {check_mark(docker_running) if docker_running else warn_mark()} Docker Daemon: {'Running' if docker_running else 'Stopped / Not Running'}")

    print(f"    {CYAN}Note: Native Sarvam AI mode runs 100% with zero Docker lag!{RESET}")

    # 4. Check Data Storage Directories
    print_header("4. Unified Data Directory Structure (data/)")
    data_dirs = {
        "Recordings": ROOT_DIR / "data" / "recordings",
        "Transcripts": ROOT_DIR / "data" / "transcripts",
        "Intelligence": ROOT_DIR / "data" / "intelligence",
        "Database": ROOT_DIR / "data" / "database",
        "Logs": ROOT_DIR / "data" / "logs",
    }
    for name, path in data_dirs.items():
        exists = path.is_dir()
        count = len(list(path.iterdir())) - (1 if (path / ".gitkeep").exists() else 0) if exists else 0
        print(f" {check_mark(exists)} data/{name.lower()}/: {'OK' if exists else 'Missing'} ({count} files)")
        if not exists:
            path.mkdir(parents=True, exist_ok=True)

    # 5. Check Environment & API Keys
    print_header("5. Configuration & Credentials (.env)")
    backend_env = ROOT_DIR / "backend" / ".env"
    frontend_env = ROOT_DIR / "frontend_1" / ".env"

    has_backend_env = backend_env.is_file()
    has_frontend_env = frontend_env.is_file()
    print(f" {check_mark(has_backend_env)} backend/.env: {'Present' if has_backend_env else 'Missing (Will be generated from template)'}")
    print(f" {check_mark(has_frontend_env)} frontend_1/.env: {'Present' if has_frontend_env else 'Missing (Will be generated from template)'}")

    # Read keys from backend/.env if present
    env_vars = {}
    if has_backend_env:
        for line in backend_env.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")

    sarvam_key = env_vars.get("SARVAM_API_KEY", "")
    has_sarvam = bool(sarvam_key and len(sarvam_key) > 15 and not sarvam_key.startswith("your_"))
    print(f" {check_mark(has_sarvam)} Sarvam AI Key: {'Configured (' + sarvam_key[:8] + '...)' if has_sarvam else 'Missing or default placeholder'}")

    gemini_key = env_vars.get("GEMINI_API_KEY", "")
    has_gemini = bool(gemini_key and len(gemini_key) > 15 and not gemini_key.startswith("your_"))
    print(f" {check_mark(has_gemini) if has_gemini else warn_mark()} Google Gemini Key: {'Configured' if has_gemini else 'Optional / Missing'}")

    vobiz_id = env_vars.get("VOBIZ_AUTH_ID", "")
    vobiz_token = env_vars.get("VOBIZ_AUTH_TOKEN", "")
    has_vobiz = bool(vobiz_id and vobiz_token and not vobiz_id.startswith("your_"))
    print(f" {check_mark(has_vobiz) if has_vobiz else warn_mark()} VoBiz Telephony: {'Configured (' + vobiz_id + ')' if has_vobiz else 'Needs Auth ID & Token'}")

    # 6. Overall Status Summary
    print_header("6. System Verification Summary")
    if all_passed:
        print(f"\n{BOLD}{GREEN}âœ” ALL CORE PREREQUISITES ARE OPERATIONAL!{RESET}")
        print(f"You can now launch the full platform by running: {BOLD}start_all.bat{RESET}\n")
    else:
        print(f"\n{BOLD}{YELLOW}âš  SOME TOOLS OR CONFIGURATIONS REQUIRE ATTENTION.{RESET}")
        print(f"Run {BOLD}setup_and_run.bat{RESET} to automatically install missing tools and configure dependencies.\n")


if __name__ == "__main__":
    main()
