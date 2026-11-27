# Saved settings adapter

Server 0.2.1 has 25 tools: the existing 19 native model tools plus six settings tools.
The settings tools also work with listener 0.1.2. Reload the MCP client after updating the Python source;
settings inspection itself does not require running the in-app listener.

## Scope

`bazis_settings_catalog` inventories an explicit list of BAZIS configuration files
under the current Windows user's `%APPDATA%/Bazis`. Each file is reported as readable
or unsupported. The adapter excludes online/account configuration and the large
render-material cache. It is not a database catalogue adapter.

`bazis_settings_read` reads saved values, hierarchical IDs, profile names, file
revision and whether a field can be staged. Query words match all of those plus
known Romanian drawing-setting labels. Results are paginated. Numeric values 0/1
remain numeric: they may be flags, enums, counters or identifiers.

These files contain configuration entries, cached selections, table columns and
window positions as well as toggles. Entry count is not the number of UI toggles.
Readable files do not prove complete application coverage or live UI access.
Unsaved dialogs may differ from saved values.

BAZIS sometimes writes numeric element names and text control characters that
strict XML parsers reject. A bounded scanner handles balanced saved markup without
normalizing the document. Binary formats, CDATA, mixed content, DTDs and external
entities are explicitly unsupported. The four binary cabinet/door/drawer files
found during validation still need their own adapter.

## Workflow

1. Inventory files and read the intended setting. Retain `setting_id`, `value` and `revision`.
2. Stage explicit changes with `file_id`, `expected_revision` and a `changes` list:

   ```json
   {"setting_id": "<ID returned by read>", "expected_value": "Y", "value": false}
   ```

   JSON booleans map to the field's original Y/N or true/false encoding. Numbers are
   finite, integer fields stay integer and text is escaped. No nodes are added or
   removed. Empty self-closing fields and oversized values need dedicated adapters.
3. Inspect the returned diff and `preview_file`. This changes only a private copy.
4. Save work and close BAZIS applications before `bazis_settings_apply(stage_id)`.
   The tool checks running processes twice near the atomic file replacement and
   refuses writes while known BAZIS modules are running. It never terminates apps.
5. Reopen BAZIS and validate that it loads the saved setting as intended. This has
   not yet been confirmed in the production installation. A specific numeric enum
   or packed flag must be mapped before being changed.
6. `bazis_settings_restore(stage_id)` restores the exact original bytes, again with
   BAZIS closed. It refuses if the active file has changed since apply; later edits
   require a new read and an explicit merge, not a blind restore.

Original/modified files, diffs and journals stay beside the private bridge config
under `~/.bazis-mcp/settings/<stage_id>/`, never inside release sources.
`allow_edits=false` blocks staging, applying and restoring.

## Conflict and crash handling

Source revision and expected old values must match. Integrity hashes validate both
stage files. Adapter writers share an exclusive per-file lock. Apply/restore journal
the intended replacement before writing; inspect `bazis_settings_result` after any
timeout or uncertain outcome. It reports both manifest state and whether the active
file matches the before/after hashes. Never replay a mutation blindly.

The process check is not an OS lock against manually starting BAZIS during a write.
Keep BAZIS closed for the entire operation. If a crash leaves an adapter lock, inspect
the stage/journal and active hash before manually removing that private lock file.

## Live UI access

This adapter does not toggle controls in a currently open dialog. Native script/API
support or an accessible Windows window is a separate integration path. An elevated
BAZIS process was not targetable from the ordinary computer-use session during the
initial validation. Normal application startup is required for the next UI test;
success remains to be verified, not assumed from the saved-settings tools. A subsequent
normal restart/launch still did not produce a targetable window in the helper, so
removing elevation alone has not resolved access. No production toggles were changed.
