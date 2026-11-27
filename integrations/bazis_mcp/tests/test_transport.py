import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from bazis_mcp.transport import BridgeClient, BridgeError, atomic_json, read_json

REPO = Path(__file__).resolve().parents[1]
NODE = os.environ.get("BAZIS_TEST_NODE") or shutil.which("node")


class LocalFileTests(unittest.TestCase):
    def test_atomic_json_unicode_and_no_temp_files(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "state.json"
            atomic_json(target, {"name": "Poliță"})
            atomic_json(target, {"name": "Verticală"})
            self.assertEqual(read_json(target)["name"], "Verticală")
            self.assertEqual(len(list(Path(d).iterdir())), 1)

    def test_offline_and_private_config_not_returned(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / "config.json"
            atomic_json(config, {"token": "private" * 10, "bridge_dir": d})
            status = BridgeClient(config).status()
            self.assertFalse(status["connected"])
            self.assertNotIn("private", json.dumps(status))

    def test_request_id_path_traversal_rejected(self):
        with self.assertRaises(BridgeError):
            BridgeClient().result("../config.json")

@unittest.skipUnless(NODE, "Set BAZIS_TEST_NODE or install Node to run the mock integration")
class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bazis-mcp-integration-")
        self.home = Path(self.temp.name)
        self.runtime = self.home / "runtime"
        self.runtime.mkdir()
        self.config = self.home / ".bazis-mcp" / "config.json"
        atomic_json(self.config, {"token": "integration-test-" * 4, "bridge_dir": str(self.runtime),
                                  "allow_edits": True, "poll_interval_ms": 100})
        self.client = BridgeClient(self.config)
        self.process = subprocess.Popen([NODE, str(REPO / "tests" / "mock-bazis.cjs"), str(self.home)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(80):
            if self.client.status()["connected"]:
                break
            if self.process.poll() is not None:
                raise RuntimeError(self.process.stderr.read().decode())
            await asyncio.sleep(0.05)
        self.assertTrue(self.client.status()["connected"])

    async def asyncTearDown(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.process.stderr.close()
        self.temp.cleanup()

    async def test_repeated_round_trips_and_parallel_reads(self):
        results = await asyncio.gather(*(self.client.call("ping") for _ in range(5)))
        self.assertTrue(all(r["pong"] for r in results))
        self.assertEqual(len({r["request_id"] for r in results}), 5)
        self.assertEqual(len({r["session_id"] for r in results}), 1)

    async def test_model_read_edit_and_journal(self):
        model = await self.client.call("get_model")
        items = await self.client.call("list_objects", {"recursive": True})
        object_id = items["items"][0]["object_id"]
        result = await self.client.call("set_properties", {"object_ids": [object_id], "model_token": model["model_token"], "name": "Test nou"})
        self.assertEqual(result["changed"][0]["name"], "Test nou")
        self.assertEqual(self.client.result(result["request_id"])["result"]["changed"][0]["name"], "Test nou")
        receipt = read_json(self.runtime / "journal" / (result["request_id"] + ".json"))
        self.assertEqual(receipt["state"], "completed")

    async def test_model_guard_and_errors(self):
        with self.assertRaisesRegex(BridgeError, "MODEL_CHANGED"):
            await self.client.call("create_panel", {"model_token": "stale"})
        with self.assertRaisesRegex(BridgeError, "UNKNOWN_METHOD"):
            await self.client.call("arbitrary_eval", {"code": "malicious"})

    async def test_timeout_cancels_queue_without_retry(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        atomic_json(self.runtime / "status.json", {"state": "ready", "updated_at_ms": int(time.time()*1000), "session_id": "paused"})
        with self.assertRaisesRegex(BridgeError, "outcome may be unknown"):
            await self.client.call("ping", timeout=0.15)
        requests = list((self.runtime / "inbox").glob("*.json"))
        self.assertEqual(len(requests), 1)
        self.assertTrue((self.runtime / "cancel" / requests[0].name).exists())

    async def test_sdk_stdio_handshake_tools_and_calls(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        saved_root = self.home / 'Bazis'
        saved_root.mkdir()
        settings_file = saved_root / 'Settings.xml'
        settings_file.write_text('<Settings><Enabled>Y</Enabled></Settings>', encoding='utf-8')
        presence_path = self.runtime / 'client-heartbeat.json'
        atomic_json(presence_path, {'legacy_presence': 'must not be modified or renewed'})
        original_presence = presence_path.read_bytes()
        env = dict(os.environ, BAZIS_MCP_CONFIG=str(self.config), APPDATA=str(self.home))
        parameters = StdioServerParameters(command=sys.executable, args=["-m", "bazis_mcp.server"], env=env, cwd=str(REPO))
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                self.assertEqual(len(tools), 25)
                names = {t.name: t for t in tools}
                self.assertTrue(names["bazis_delete_objects"].annotations.destructiveHint)
                self.assertTrue(names["bazis_get_model"].annotations.readOnlyHint)
                self.assertTrue(names["bazis_settings_read"].annotations.readOnlyHint)
                saved = await session.call_tool('bazis_settings_read', {'file_id': 'Settings.xml'})
                self.assertFalse(saved.isError)
                setting = saved.structuredContent['items'][0]
                staged = await session.call_tool('bazis_settings_stage', {
                    'file_id': 'Settings.xml', 'expected_revision': saved.structuredContent['revision'],
                    'changes': [{'setting_id': setting['setting_id'], 'expected_value': 'Y', 'value': False}]})
                self.assertFalse(staged.isError)
                self.assertEqual(staged.structuredContent['changes'][0]['after'], 'N')
                self.assertEqual(settings_file.read_text(encoding='utf-8'), '<Settings><Enabled>Y</Enabled></Settings>')
                staged_result = await session.call_tool('bazis_settings_result', {'stage_id': staged.structuredContent['stage_id']})
                self.assertEqual(staged_result.structuredContent['current_matches'], 'before')
                ping = await session.call_tool("bazis_ping", {})
                self.assertFalse(ping.isError)
                self.assertTrue(ping.structuredContent["pong"])
                self.assertEqual(presence_path.read_bytes(), original_presence)
                model = await session.call_tool("bazis_get_model", {})
                self.assertEqual(model.structuredContent["top_level_count"], 2)
                invalid = await session.call_tool("bazis_create_panel", {"model_token": "x", "name": "x", "orientation": "front", "width": -1, "height": 100, "thickness": 18})
                self.assertTrue(invalid.isError)
        self.assertEqual(presence_path.read_bytes(), original_presence)


if __name__ == "__main__":
    unittest.main()
