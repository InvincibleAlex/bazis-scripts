# BAZIS Woodworker MCP

Local MCP server plus a persistent JavaScript listener inside BAZIS Woodworker.
Server/listener 0.2.2 use manual startup and a stable status label. The saved-settings adapter is retained.
The first adapter targets the legacy `Model`, `Action`, `system` scripting API.
The user's diagnostic confirmed embedded Node **8.11.3 / ia32**, `system.apiVersion=2341`,
and a successful file exchange. Those values identify a tested runtime profile;
they are not a claim that every BAZIS release works.

## Quick start / Pornire

1. Install Python 3.11+ and Node 18+ for development tests. BAZIS uses its own embedded Node.
2. Create an isolated environment, install dependencies and register the MCP:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe install.py --register-codex
```

3. In BAZIS: **Scripts → Script editor → Open → `Codex_Bazis_Bridge.js` → Run/F5**.
   The installer copies it to `Documents\Bazis\Scripts`. Use `--scripts-dir` for another location.
   The listener stays active for this manually started session. Its stable hint says `Codex MCP activ`.
   An action-local key handler suppresses Escape cancellation and stops on the physical grave/backtick
   key below Escape (VK_OEM_3=192 on the target layout). `bazis_stop_bridge` and editor Stop also work.
4. Restart/reload the MCP client so it loads `bazis`, then call `bazis_status`, `bazis_ping`,
   `bazis_get_model`, and `bazis_list_objects`. Use the returned `model_token` and object IDs for edits.

If BAZIS shows a missing-config error, run install.py under the same Windows account that runs BAZIS.
The listener defaults to `%USERPROFILE%\.bazis-mcp\config.json`.
The server can use `BAZIS_MCP_CONFIG` to select a different config, but the listener's config path
must also be changed for that non-default setup.

## Tools

| Tools | Purpose |
|---|---|
| `bazis_status`, `bazis_ping`, `bazis_capabilities` | Health, round trip, implemented handlers and detected API |
| `bazis_get_model`, `bazis_list_objects`, `bazis_get_object`, `bazis_get_selection` | Inspect the active model, hierarchy, materials, bounds and machining counts |
| `bazis_select_objects`, `bazis_set_view` | Select objects, change camera and fit model |
| `bazis_set_properties` | Name, visibility, position label and designation |
| `bazis_move_objects`, `bazis_rotate_objects`, `bazis_duplicate_objects` | Global transforms and copies |
| `bazis_create_panel`, `bazis_create_cabinet` | Rectangular panels and simple cabinet blocks |
| `bazis_delete_objects` | Delete explicit object IDs in an undoable operation |
| `bazis_save_model_copy` | Save a new B3D under runtime `exports/`; refuses existing files |
| `bazis_request_result`, `bazis_stop_bridge` | Resolve uncertain outcomes; stop listener |
| `bazis_settings_catalog`, `bazis_settings_read` | Inventory/search saved BAZIS configuration; not unsaved dialogs |
| `bazis_settings_stage`, `bazis_settings_result` | Prepare a private modified copy with before/after diff; inspect outcome |
| `bazis_settings_apply`, `bazis_settings_restore` | Apply or restore an exact settings change while BAZIS apps are closed |

Units: **mm**, angles: **degrees**. BAZIS axes: X width, Y height, Z depth.
Rotation uses a global axis through the **global origin**, not the center of each object.
Panel dimensions follow the tool description for each orientation.
Cabinet construction uses full-height sides and inset top/bottom, with an optional applied back;
the applied back increases depth by its thickness. It adds no doors, fittings, holes or production checks.
If no material is supplied, BAZIS's active material is used, including for the back unless overridden.

Saved settings use separate, revision-checked operations and can be read without starting the listener.
See [Saved settings](docs/SETTINGS.md) for scope, limitations and application workflow.

## Operational behavior

- This is a bounded tool set, not a wrapper around every BAZIS menu action.
- The listener receives only named JSON commands. It never evaluates arbitrary JavaScript or shell commands.
- Config and queue data stay under `~/.bazis-mcp/`, outside this repository. No user models are included.
- Set `allow_edits` to `false` in local config and restart the listener for inspection-only use.
- One listener owns a runtime folder. Finish the old listener before starting another.
- Startup/restart is manual (Run/F5); there is no MCP presence lease, connection indicator monitor
  or automatic script relaunch. Queue polling and the local status heartbeat remain necessary to
  receive explicit commands and tell whether the listener is running.
- Edits register with `StartEditing(Model)` and commit through `Action.Commit`. On failure,
  `Action.Revert` is requested. Native BAZIS rollback behavior still needs live validation.
- Committing changes to BAZIS history does **not** save the B3D to disk. Saving is an explicit tool.
- A committed creation may become discoverable only on a later native model read. When a creation
  returns `committed=true` and `object_lookup_pending=true`, call `bazis_list_objects` next; do not
  repeat the creation. Optional panel/cabinet snapshots may be null in that response.
- A model switch invalidates the model token. Object handles also validate their path and identity;
  refresh the object list after manual structural changes, deletion or undo.
- Requests are atomically claimed and journaled before execution. A request ID is never re-executed.
  A crash between editing and writing the result can leave an unknown outcome. Never blindly retry a write.
- Expired/cancelled queued commands are refused. An already executing native operation cannot be safely interrupted.
- A failed save/copy can leave a new partial output file; inspect it before retrying with a different name.
- Queues/journals persist for diagnosis. Archive old runtime data only while the listener is stopped.
- Some BAZIS versions may reserve the current action while a persistent script runs. If normal UI work
  finishes/cancels the script, restart it. Continuous listening across all UI operations is not guaranteed.
- Escape suppression uses native action key preview and mutable key references; verify a real Escape press
  on the installed build. `status.json.escape_protection` shows whether handlers were installed and how many
  Escape events they consumed. `stop_key` reports the configured stop key and intercepted stops.
  Native keyboard event delivery still requires verification. No global Windows keyboard hook is installed.

## Validation

```powershell
node tests/test_bridge.cjs
node tests/test_drawing_probe.cjs
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests use an isolated mock BAZIS model and real temporary file queues, never a production model.
`docs/LIVE-VALIDATION.md` distinguishes mock verification from native BAZIS results.
The persistent listener has now passed live MCP read checks in BAZIS: repeated pings, model
summary, recursive listing and individual object details. Native panel movement, single-panel creation,
selection and camera fitting have also passed. Native rollback remains unvalidated.
In v0.1.0, `bounds_parent_mm` contains native `GMin/GMax`, observed as object-local bounds on
rotated panels; use `bounds_global_mm` for world extents.

## Updating and GitHub

Planned extensions and verified settings findings: [Plan de extindere](docs/PLAN-RO.md).

This folder is suitable for a Git repository. `.venv`, `.local`, reports, models and runtime data are excluded.
No remote repository is created or published by the installer. Review the diff, tag a version, then push to your own remote.
After pulling an update, install its locked requirements, rerun install.py, stop the old listener and run the updated
listener in BAZIS. Reload the MCP client. Code is not downloaded or executed automatically from GitHub.

## Sources

- [BAZIS scripting documentation](https://bazissoft.ru/file/guide/skript)
- [Legacy scripting user guide (2021)](https://s3-cold.bazissoft.ru/documentation/en/Script.pdf)
- [Official BAZIS script examples](https://github.com/BazisSoft/Scripts)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

## License

MIT; see LICENSE. This project is independent of BAZIS and OpenAI.
