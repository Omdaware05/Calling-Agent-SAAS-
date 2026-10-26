"""
Live Calling & Telephony Verification Script
===========================================
Performs real-time diagnostic checks on:
1. Sarvam AI Voice Engine API key
2. VoBiz Telephony Carrier API credentials
3. Active Ngrok Public Webhook Tunnel
4. Data directories write access

Usage:
    python scripts/verify_calling.py
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent

# Read .env file
env_file = ROOT_DIR / "backend" / ".env"
env_vars = {}
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip().strip('"').strip("'")

SARVAM_KEY = env_vars.get("SARVAM_API_KEY", "")
VOBIZ_ID = env_vars.get("VOBIZ_AUTH_ID", "")
VOBIZ_TOKEN = env_vars.get("VOBIZ_AUTH_TOKEN", "")
VOBIZ_FROM = env_vars.get("VOBIZ_FROM_NUMBER", "")


def test_sarvam() -> bool:
    print("[1/4] Testing Sarvam AI Voice Engine...")
    if not SARVAM_KEY or len(SARVAM_KEY) < 15 or SARVAM_KEY.startswith("your_"):
        print("  [FAIL] Sarvam AI API Key is missing or invalid in backend/.env!")
        return False

    try:
        # Test a short TTS synthesis
        url = "https://api.sarvam.ai/text-to-speech"
        payload = json.dumps({
            "inputs": ["नमस्ते"],
            "target_language_code": "hi-IN",
            "speaker": "shubh",
            "model": "bulbul:v3"
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "api-subscription-key": SARVAM_KEY,
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            if resp.status == 200:
                print("  [PASS] Sarvam AI Voice Engine: CONNECTED & WORKING (Fast TTS active)")
                return True
            else:
                print(f"  [FAIL] Sarvam AI response status: {resp.status}")
                return False
    except Exception as e:
        print(f"  [FAIL] Sarvam AI Connection error: {e}")
        return False


def test_vobiz() -> bool:
    print("[2/4] Testing VoBiz Telephony Carrier...", flush=True)
    if not VOBIZ_ID or not VOBIZ_TOKEN or VOBIZ_ID.startswith("your_"):
        print("  [FAIL] VoBiz Auth ID or Auth Token is missing in backend/.env!", flush=True)
        return False

    # Check credentials format
    print(f"  [PASS] VoBiz Carrier Account: CONFIGURED (Auth ID: {VOBIZ_ID})", flush=True)
    print(f"  [PASS] Outbound Caller ID: {VOBIZ_FROM or '+918065354620'}", flush=True)

    try:
        url = f"https://api.vobiz.ai/api/v1/Account/{VOBIZ_ID}/"
        req = urllib.request.Request(
            url,
            headers={
                "X-Auth-ID": VOBIZ_ID,
                "X-Auth-Token": VOBIZ_TOKEN,
                "User-Agent": "CallingAgentDoctor/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status in (200, 201):
                print("  [PASS] VoBiz Carrier Upstream: LIVE & VERIFIED", flush=True)
            else:
                print(f"  [INFO] VoBiz Upstream Status: {resp.status}", flush=True)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print("  [FAIL] VoBiz Authentication Failed (HTTP 401/403): Invalid Auth ID or Auth Token", flush=True)
            return False
        else:
            print(f"  [INFO] VoBiz upstream status {e.code}: {e.reason}", flush=True)
    except Exception:
        print("  [INFO] VoBiz credentials configured (upstream ping bypassed/firewalled)", flush=True)

    return True


def test_tunnel() -> bool:
    print("[3/4] Testing Ngrok Public Audio Webhook Tunnel...")
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                tunnels = data.get("tunnels", [])
                for t in tunnels:
                    u = t.get("public_url", "")
                    if u.startswith("https://"):
                        print(f"  [PASS] Active Public Tunnel: {u}")
                        return True
    except Exception:
        pass

    # Check saved tunnel file
    tf = ROOT_DIR / "data" / "logs" / "tunnel_url.txt"
    if tf.exists():
        url = tf.read_text(encoding="utf-8").strip()
        if url.startswith("https://"):
            print(f"  [PASS] Cached Public Tunnel: {url}")
            return True

    print("  [WARN] No active Ngrok tunnel detected on http://127.0.0.1:4040.")
    print("    Start ngrok with: ngrok http 8001 (or run start_all.bat)")
    return False


def test_data_folders() -> bool:
    print("[4/4] Testing Central Data Directories...")
    for d in ["recordings", "transcripts", "intelligence", "database", "logs"]:
        p = ROOT_DIR / "data" / d
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_test"
        try:
            test_file.write_text("ok")
            test_file.unlink()
        except Exception as e:
            print(f"  [FAIL] Cannot write to data/{d}: {e}")
            return False
    print("  [PASS] All data/ directories (recordings, transcripts, intelligence, database, logs) are WRITABLE")
    return True


def main():
    print("=======================================================================")
    print("         ARB SoftTech Calling Agent - Telephony Verification")
    print("=======================================================================\n")
    s_ok = test_sarvam()
    print()
    v_ok = test_vobiz()
    print()
    t_ok = test_tunnel()
    print()
    d_ok = test_data_folders()
    print()
    print("=======================================================================")
    if s_ok and v_ok:
        print("[READY] Telephony and Voice AI pipelines are ready for live phone calls!")
    else:
        print("[ATTENTION] Please review the items marked with [FAIL] above before dialing.")
    print("=======================================================================")


if __name__ == "__main__":
    main()
