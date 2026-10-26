"""
1-Click Automated Client Packaging Tool
=======================================
Generates a clean, lightweight, production-ready ZIP archive of the entire
calling agent repository for sharing with clients via GitHub, Google Drive,
OneDrive, or email.

Automatically excludes node_modules, Python virtual environments, Git history,
large caches, and runtime databases to produce a clean ~10 MB archive.

Usage:
    python package_for_client.py
"""

import os
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_ZIP = ROOT_DIR / "arb_calling_agent_client_package.zip"

EXCLUDE_DIRS = {
    ".git",
    ".vscode",
    ".idea",
    ".pytest_cache",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    ".npm",
    "reports",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".tar.gz",
    ".zip",
    ".log",
    ".wav",
    ".mp3",
}

EXCLUDE_EXACT_FILES = {
    "arb_calling_agent_client_package.zip",
    "calling_agent.db",
    "calling_agent.db-wal",
    "calling_agent.db-shm",
}


def should_exclude(path: Path) -> bool:
    rel_parts = path.relative_to(ROOT_DIR).parts
    for part in rel_parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.startswith(".pytest"):
            return True

    if path.name in EXCLUDE_EXACT_FILES:
        return True

    # Allow .gitkeep inside data directories
    if path.name == ".gitkeep":
        return False

    if path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True

    return False


def create_client_package():
    print(f"Creating clean client package: {OUTPUT_ZIP.name}...")
    if OUTPUT_ZIP.exists():
        try:
            OUTPUT_ZIP.unlink()
        except Exception:
            pass

    included_count = 0
    total_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(ROOT_DIR):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".venv")]

            for file in files:
                file_path = Path(root) / file
                if should_exclude(file_path):
                    continue

                rel_path = file_path.relative_to(ROOT_DIR)
                zip_file.write(file_path, arcname=str(rel_path))
                included_count += 1
                total_bytes += file_path.stat().st_size

    size_mb = total_bytes / (1024 * 1024)
    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print("=" * 65)
    print("SUCCESS: Client package created successfully!")
    print(f"Files included:    {included_count}")
    print(f"Uncompressed size: {size_mb:.2f} MB")
    print(f"Compressed size:   {zip_size_mb:.2f} MB")
    print(f"Package location:  {OUTPUT_ZIP}")
    print("=" * 65)
    print("You can now safely upload this clean package or push to GitHub for your client.")


if __name__ == "__main__":
    create_client_package()
