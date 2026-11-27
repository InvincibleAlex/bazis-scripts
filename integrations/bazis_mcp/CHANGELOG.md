# Changelog

## 0.2.2 — 2026-10-16

- Native test confirmed movement of two panels and creation of one rectangular panel, followed by
  independent model reads, selection and camera fitting. No B3D was saved.
- Fixes a misleading NOT_IN_MODEL error after a creation has already committed: if immediate object
  lookup is unavailable, return a committed receipt with object_lookup_pending=true. Read the object
  list next; never repeat creation. The same response behavior covers copies and cabinet creation.
- Uses the current object returned by model traversal for resolved creation snapshots.
- Adds delayed-publication/no-duplicate regression coverage. Nineteen Python tests and 56 JavaScript
  checks pass; native validation of the new receipt awaits restarting the updated listener.

## 0.2.1 — 2026-10-16

- Returns to manual listener startup with stable `Codex MCP activ` text; removes the live connected/
  disconnected indicator and Python presence-renewal task. Old presence files are ignored.
- Stops on the physical grave/backtick key below Escape (VK_OEM_3=192); Escape is consumed by
  the script action. Numpad zero (96) is left alone. Original key handlers are restored on stop.
- A stop key received during a command is deferred until that command completes. Stop does not relaunch.
- Keeps the command-queue polling and local heartbeat needed for manually started MCP sessions.
- Keeps the saved-settings tools. Nineteen Python tests and 51 JavaScript checks pass; native key
  interception and startup of this updated listener await a manual Run/F5 in BAZIS.

## 0.2.0 — 2026-10-16

- Adds six MCP tools for saved-settings inventory, search/read, stage, apply, restore and outcome inspection.
- Dedicated disk adapter preserves every byte outside requested leaf values, including BOM/newlines,
  numeric BAZIS tag names, Unicode names and legacy control characters.
- Stage requires an exact file revision and expected old values; leaves the active file unchanged.
- Apply/restore require BAZIS applications closed, retain the original bytes, check conflicts/integrity,
  serialize adapter writes and journal uncertain outcomes. They never close applications or save models.
- Distinguishes mapped drawing labels from raw fields/enums; blocks sensitive and script-launch fields.
- Validated catalog/read through real MCP stdio against local saved settings, and a one-field drawing
  preview with an unchanged active configuration. Live-dialog editing is not implemented by this adapter.
- Twenty Python tests and 48 JavaScript checks pass. Compatible in-app listener remains 0.1.2.

## 0.1.2 — 2026-10-16

- Installs action-local key preview/down/up handlers that consume mutable Escape key references.
- Keeps polling while disconnected and reconnects automatically when the MCP presence lease returns.
- Removes the Escape-to-stop hint; explicit MCP stop/editor stop remains available.
- Reports handler installation and ignored Escape event count in status/capabilities for native verification.
- The Escape guard is mock-tested; actual keyboard dispatch in the installed legacy build still needs a live press test.

## 0.1.1 — 2026-10-16

- BAZIS info bar shows `✓ Codex conectat` or `○ Codex deconectat` according to a live MCP presence lease.
- The MCP process renews its session-bound lease every two seconds, including while no tool is called.
- Expired, mismatched and invalid presence records do not report a connection; stale leases expire after seven seconds.
- Uses the documented `Action.Hint` text with a leading symbol; does not change undocumented native HintKind/icon values.
- Added indicator transition, presence ownership and MCP-lifecycle tests.

## 0.1.0 — 2026-10-16

- Legacy BAZIS adapter with 19 MCP tools.
- Persistent, local file-queue listener compatible with embedded Node 8.
- Model guards, stale object checks, atomic requests, expiry, cancellation and request journaling.
- Explicit panel/cabinet, property, selection, transform, copy, delete and save-copy operations.
- Local installer, Codex configuration backup, version-locked dependencies and release packaging.
- Mock native-model tests and a real MCP stdio handshake/integration test.
- Native diagnostic confirmed API/file access. Persistent-listener MCP read calls subsequently passed
  in BAZIS without rerunning the script. Native edit/rollback testing remains pending.
- Documented the v0.1.0 local-bound naming caveat discovered during the native read checks.
