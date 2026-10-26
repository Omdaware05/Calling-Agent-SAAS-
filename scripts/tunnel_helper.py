"""
Tunnel Helper Script
====================
Detects or polls the active Ngrok public URL and persists it to data/logs/tunnel_url.txt.
Ensures zero delay for telephony webhook resolution.
"""

import sys
import time
import json
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT_DIR / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
TUNNEL_FILE = LOGS_DIR / "tunnel_url.txt"


def get_ngrok_url(max_retries: int = 15, delay: float = 1.0) -> str:
    """
    Polls the local Ngrok client API at http://127.0.0.1:4040/api/tunnels
    until a public HTTPS URL is assigned.
    """
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "TunnelHelper/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    tunnels = data.get("tunnels", [])
                    for t in tunnels:
                        u = t.get("public_url", "")
                        if u.startswith("https://"):
                            return u.rstrip("/")
        except Exception:
            pass
        time.sleep(delay)
    return ""


def main():
    target_port = 8001
    if len(sys.argv) > 1:
        try:
            target_port = int(sys.argv[1])
        except ValueError:
            pass

    url = get_ngrok_url(max_retries=15, delay=1.0)
    if url:
        TUNNEL_FILE.write_text(url, encoding="utf-8")
        print(f"ACTIVE_TUNNEL_URL={url}")
        sys.exit(0)
    else:
        print("NO_TUNNEL_DETECTED")
        sys.exit(1)


if __name__ == "__main__":
    main()
