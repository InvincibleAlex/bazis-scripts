"""Install/update the listener and optionally register this local MCP in Codex."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import secrets
import shutil
import sys

from bazis_mcp.transport import atomic_json, default_config, read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts-dir", type=Path, default=Path.home() / "Documents" / "Bazis" / "Scripts")
    parser.add_argument("--bridge-dir", type=Path)
    parser.add_argument("--register-codex", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent
    config_path = default_config()
    if config_path.exists():
        config = read_json(config_path)
    else:
        config = {"protocol": 1, "token": secrets.token_hex(32), "allow_edits": True, "poll_interval_ms": 250,
                  "bridge_dir": str((config_path.parent / "runtime").resolve())}
    if args.bridge_dir:
        config["bridge_dir"] = str(args.bridge_dir.resolve())
    bridge_dir = Path(config["bridge_dir"])
    for subfolder in ("inbox", "processing", "outbox", "journal", "cancel", "exports"):
        (bridge_dir / subfolder).mkdir(parents=True, exist_ok=True)
    atomic_json(config_path, config)
    args.scripts_dir.mkdir(parents=True, exist_ok=True)
    destination = args.scripts_dir / "Codex_Bazis_Bridge.js"
    for name in (destination.name, "Codex_Bazis_DrawingAPI_Probe.js"):
        script_destination = args.scripts_dir / name
        source = repo / "bridge" / name
        if script_destination.exists() and script_destination.read_bytes() != source.read_bytes():
            backup_dir = config_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(script_destination, backup_dir / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + name))
        shutil.copy2(source, script_destination)
    local_dir = repo / ".local"
    local_dir.mkdir(exist_ok=True)
    entry = {"command": sys.executable, "args": ["-m", "bazis_mcp.server"], "cwd": str(repo),
             "env": {"BAZIS_MCP_CONFIG": str(config_path)}, "tool_timeout_sec": 35, "enabled": True}
    atomic_json(local_dir / "mcp-config.json", {"mcpServers": {"bazis": entry}})
    if args.register_codex:
        import tomlkit
        codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        target = codex_home / "config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        original = target.read_text(encoding="utf-8") if target.exists() else ""
        document = tomlkit.parse(original)
        servers = document.setdefault("mcp_servers", tomlkit.table())
        if "bazis" in servers and dict(servers["bazis"]) != entry:
            existing = servers["bazis"]
            if list(existing.get("args", [])) != ["-m", "bazis_mcp.server"]:
                raise RuntimeError("A different MCP named bazis already exists; choose a different name manually")
        servers["bazis"] = entry
        if target.exists():
            backup_dir = config_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_dir / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-codex-config.toml"))
        temp = target.with_name("config.bazis-mcp.tmp")
        temp.write_text(tomlkit.dumps(document), encoding="utf-8")
        os.replace(temp, target)
        print("Registered MCP: bazis (restart/reload the MCP client to load tools)")
    print("BAZIS listener:", destination)
    print("Bridge runtime:", bridge_dir)
    print("Local config:", config_path, "(keep private; do not commit)")
    print("Run the listener once in BAZIS, then use bazis_status and bazis_ping")


if __name__ == "__main__":
    main()
