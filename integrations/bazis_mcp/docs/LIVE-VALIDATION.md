# Validation record

## Confirmed inside the user's BAZIS installation

The preceding diagnostic ran successfully and reported:

- Node 8.11.3, ia32; legacy API 2341 / compatibility value 1101.
- Read/write using `require('fs')`.
- A request nonce prepared outside BAZIS was returned correctly.
- Model properties and a four-object top-level sample were read successfully.
- Legacy editing functions were detected, but not called by that diagnostic.

## Persistent bridge: native read validation passed — 2026-10-16

The listener was started manually in BAZIS. The configured MCP connector successfully executed
model summary, two independent pings, capabilities, recursive listing, selection read and a
subsequent detail read of a previously returned object handle, in the same persistent session.
No extra Run/F5 was needed between calls. The listener remained ready with no reported error.
The model contained 4 top-level objects and 131 objects recursively. Its geometry was unchanged.

Confirmed live: persistent timer callbacks can read native BAZIS objects, the full MCP transport
works, nesting is traversed, and handles remain usable between calls. No selected object was
present; the empty selection was returned correctly. There was no filename in the native model
summary, so filename discovery for a saved model remains unvalidated.

## Native editing validation still pending

The v0.1.2 Escape guard passed mutable-reference and normal-key mock tests. Native dispatch
requires the user to restart the updated listener and press Escape in the 3D view; inspect
`escape_protection.installed` and `ignored_events` afterward. Explicit stop is still tested.

The v0.1.1 connection indicator passed simulated transition and MCP lifecycle tests; its
native visual appearance awaits restarting the listener and MCP process after this update.

Geometry edits, selection/camera writes, saving, transaction/rollback behavior and listening
across arbitrary manual UI operations had not yet been tested at the time of the initial validation. Their mock tests
are distinct from native validation. Test these on a disposable model before production use.

Coordinate caveat in v0.1.0: `bounds_parent_mm` is populated from native `GMin/GMax`; live
observations of rotated panels indicate object-local bounds despite the legacy field name.
Use `bounds_global_mm` for world extents and `position_parent_mm` for parent placement.
An explicit local-bound field name should replace the legacy label in the next API revision.

## Saved settings adapter — 2026-10-16

A fresh real MCP stdio session with server 0.2.0 listed 25 tools, inventoried local
saved configuration, searched a drawing-profile field, staged Y -> N for a single
gabarit-dimension setting and inspected the stage. The original CreateDrawings.xml
SHA-256 remained unchanged. Only a private preview and before/after journal were
created. Applying that preview to the production configuration was not attempted.

The adapter read 44 of 48 inventoried configuration files. Four files were binary
and reported unsupported: CabCurrent.xml, CabFurnSettings.xml, MasterBox.xml and
MasterDoor.xml. The 35,363 leaf entries include table metadata, cached selections
and window geometry; this is not a claim of 35,363 application toggles.

Twenty Python tests (including settings apply/restore on temporary files and true
MCP calls) and 48 JavaScript bridge checks pass. Production profile loading and
native dialog updates remain unvalidated. The configured long-running MCP process
still needs a client reload to expose the new tools; the fresh verification session
is distinct from that existing process.

The original BAZIS process was confirmed elevated while the tool process was not.
After the user restarted BAZIS, its new process was readable and responded, but the
Windows computer-use helper still returned no targetable BAZIS window. Recovery via
normal launch also returned "launched app did not expose a targetable window".
Elevation was therefore one observed condition, not a confirmed complete explanation
of the UI limitation. No Windows UI input or production setting changes were made.

## Native move/create/selection/view test — 2026-10-16

The user explicitly requested moving the two visible test panels and adding a test object.
The bridge 0.2.1 session read both object handles/UIDs, then translated both by X=100 mm,
Y=50 mm, Z=0. Independent reads confirmed those deltas and unchanged 1000 x 1000 x 18 mm
panel sizes. It created one horizontal Test MCP panel, 400 x 300 x 18 mm, using the active
OSB material. A later recursive model read found exactly three objects, including the one
new panel at X=900, Y=350, Z=250. Selection of the new object and isometric camera/fit calls
also returned successfully. These edits were committed in the active document, not saved
to a B3D file. This does not validate native rollback, deletion, duplication or cabinet creation.

The initial create response returned NOT_IN_MODEL after commit, even though the next read
found the correctly sized panel. The command was not replayed. Version 0.2.2 now returns a
committed receipt with a pending lookup if this occurs; it does not claim rollback or encourage
retry. Delayed-publication mocks and duplicate-request replay tests pass. The exact native
publication/reference timing remains uncertain and the updated receipt needs a new native run.

A fresh MCP stdio session separately listed all 25 server tools, read saved drawing settings
and staged a Y -> N gabarit-dimension preview. It verified that the active configuration hash
was unchanged. Live-dialog setting changes and production settings apply remain unvalidated.
