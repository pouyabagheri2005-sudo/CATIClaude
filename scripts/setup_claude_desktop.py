"""
scripts/setup_claude_desktop.py

One-shot installer that registers this MCP server in Claude Desktop's
config file, merging with (rather than overwriting) any existing
`mcpServers` entries.

IMPORTANT (Windows): Claude Desktop is distributed two ways on Windows:
  1. Direct-download installer (Squirrel/Electron) -> reads
     %APPDATA%\\Claude\\claude_desktop_config.json, exactly as documented.
  2. Microsoft Store app (MSIX package) -> Windows silently virtualizes
     %APPDATA% for sandboxed apps, so the app actually reads/writes:
     %LOCALAPPDATA%\\Packages\\Claude_<hash>\\LocalCache\\Roaming\\Claude\\claude_desktop_config.json
     Writing to the documented %APPDATA% path in this case has NO effect -
     Claude never sees it, and the Developer/MCP settings page will show
     no servers at all.

This script auto-detects which install you have and writes to the correct
location. Run it again any time (after moving the project, changing Python
interpreters, or reinstalling Claude) - it is idempotent and safe.

Usage:
    python scripts/setup_claude_desktop.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

SERVER_NAME = "catia"


def _find_msix_virtualized_config() -> Optional[Path]:
    """Return the real config path for a Microsoft Store (MSIX) install of
    Claude Desktop, if one is present, else None.
    """
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return None
    packages_dir = Path(local_appdata) / "Packages"
    if not packages_dir.is_dir():
        return None
    for entry in packages_dir.iterdir():
        if entry.is_dir() and entry.name.lower().startswith("claude_"):
            candidate = (
                entry
                / "LocalCache"
                / "Roaming"
                / "Claude"
                / "claude_desktop_config.json"
            )
            if candidate.exists() or candidate.parent.is_dir():
                return candidate
    return None


def get_claude_config_path() -> Path:
    if sys.platform == "win32":
        msix_path = _find_msix_virtualized_config()
        if msix_path is not None:
            print(
                f"Detected Microsoft Store (MSIX) install of Claude Desktop: {msix_path}"
            )
            return msix_path

        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError(
                "%APPDATA% is not set; cannot locate Claude Desktop config."
            )
        return Path(appdata) / "Claude" / "claude_desktop_config.json"

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )

    # Linux (unofficial Claude Desktop builds commonly use this location).
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    server_path = project_root / "server.py"
    python_exe = sys.executable

    if not server_path.exists():
        raise FileNotFoundError(f"server.py not found at {server_path}")

    config_path = get_claude_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            backup = config_path.with_suffix(".json.bak")
            config_path.replace(backup)
            print(
                f"WARNING: existing config was invalid JSON ({exc}); backed up to {backup}"
            )
            config = {}
    else:
        config = {}

    config.setdefault("mcpServers", {})
    config["mcpServers"][SERVER_NAME] = {
        "command": python_exe,
        "args": [str(server_path)],
    }

    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"Wrote Claude Desktop config: {config_path}")
    print(f"  command = {python_exe}")
    print(f"  args    = [{server_path}]")
    print(f"  servers registered = {list(config['mcpServers'].keys())}")
    print("\nFully quit and relaunch Claude Desktop for the change to take effect.")


if __name__ == "__main__":
    main()
