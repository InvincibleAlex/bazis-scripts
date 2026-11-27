"""Local, atomic file transport. Never retries a model mutation automatically."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import time
import uuid


class BridgeError(RuntimeError):
    pass


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def default_config() -> Path:
    return Path(os.environ.get("BAZIS_MCP_CONFIG", Path.home() / ".bazis-mcp" / "config.json"))


class BridgeClient:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or default_config()

    def config(self) -> dict:
        try:
            config = read_json(self.config_path)
        except (OSError, ValueError) as exc:
            raise BridgeError("Run install.py first; bridge configuration is missing or invalid") from exc
        if not isinstance(config.get("token"), str) or len(config["token"]) < 32:
            raise BridgeError("Invalid local bridge token; run install.py")
        return config

    def status(self) -> dict:
        config = self.config()
        folder = Path(config["bridge_dir"])
        try:
            heartbeat = read_json(folder / "status.json")
        except (OSError, ValueError):
            return {"connected": False, "instruction": "Run Codex_Bazis_Bridge.js in BAZIS", "bridge_dir": str(folder)}
        age = time.time() * 1000 - heartbeat.get("updated_at_ms", 0)
        return {"connected": heartbeat.get("state") == "ready" and -2000 < age < 8000,
                "heartbeat_age_seconds": round(age / 1000, 2), "bridge": heartbeat}

    async def call(self, method: str, params: dict | None = None, *, timeout: float = 25) -> dict:
        config = self.config()
        status = self.status()
        if not status["connected"]:
            raise BridgeError("BAZIS bridge is offline. Run Codex_Bazis_Bridge.js and leave it active")
        folder = Path(config["bridge_dir"])
        session = status["bridge"]["session_id"]
        request_id = uuid.uuid4().hex
        request = {"protocol": 1, "id": request_id, "token": config["token"],
                   "session_id": session, "method": method, "params": params or {},
                   "created_at_ms": int(time.time() * 1000),
                   "deadline_ms": int((time.time() + timeout) * 1000)}
        request_path = folder / "inbox" / (request_id + ".json")
        response_path = folder / "outbox" / (request_id + ".json")
        atomic_json(request_path, request)
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                if response_path.exists():
                    try:
                        response = read_json(response_path)
                    except (OSError, ValueError):
                        await asyncio.sleep(0.05)
                        continue
                    if response.get("id") != request_id or response.get("session_id") != session:
                        raise BridgeError("Response/session mismatch; inspect request journal")
                    if not response.get("ok"):
                        error = response.get("error", {})
                        raise BridgeError(f"{error.get('code', 'BRIDGE_ERROR')}: {error.get('message', 'Command failed')}")
                    return response["result"]
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            atomic_json(folder / "cancel" / (request_id + ".json"), {"id": request_id})
            raise
        atomic_json(folder / "cancel" / (request_id + ".json"), {"id": request_id})
        raise BridgeError(f"Timeout; outcome may be unknown. Do not repeat a write blindly. Request ID: {request_id}")

    def result(self, request_id: str) -> dict:
        if len(request_id) != 32 or any(c not in "0123456789abcdef" for c in request_id):
            raise BridgeError("Expected a 32-character lowercase request ID")
        folder = Path(self.config()["bridge_dir"])
        for subfolder in ("outbox", "journal"):
            path = folder / subfolder / (request_id + ".json")
            if path.exists():
                return read_json(path)
        return {"id": request_id, "state": "unknown"}
