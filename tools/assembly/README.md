# Assembly illustration prototype

The default layout begins with the complete view and exploded main assemblies.
Each cabinet/block then has its own consecutive sequence: completed view, explosion,
board/hardware inventories, then preparation immediately followed by its matching
assembly step. Only after that
does the next block begin. A final sheet shows the complete global assembly.
Each exact non-empty BAZIS designation is prepared once across the guide; subsequent
inventories reference the block containing that preparation. Empty codes are never
merged. At the user's instruction, exact code equality is authoritative for identity.

Mounting order sweeps side and horizontal boards together by their centers along
the cabinet's local left-to-right axis, across subgroups. Back and face boards
follow separately. Face boards are ordered by increasing local Z, matching their
insertion from positive local Z: deeper boards before the outer closure. This is
a geometric priority, not a swept-volume collision solver. At equal local X,
orientation and numeric designation break
ties. Names do not affect this ordering. Local centers are retained per step.
The structural group inference is used for explosion presentation only, not to
force every carcass board before shelves. Insertion paths remain schematic.

The camera applies Y=-20 degrees followed by X=+20 degrees. Each sheet chooses A4
portrait/landscape by which yields a larger fitted drawing. Geometry lines are
0.20-0.25 pt and arrows 0.35 pt. Opaque board faces depth-test line fragments;
hidden edges are omitted as vector fragments. CAD/unsupported contour occlusion
falls back to oriented bounds. Only the current board's fittings are orange;
previously assembled fittings use the same gray as old boards. Inventories are
wireframe with all fittings orange. Explosion labels use two nonzero segments:
45 degrees from the part/group center, then a horizontal landing. Text is placed
outside projected silhouettes with collision scoring. Inventories, preparation
and mounting steps retain blue numbered circles.

Fitting explosions are axial only. Native exports derive shaft axes from the
local frame and local bounds of elongated screw/dowel leaves, combining parallel
axes within a composite. Existing reports can infer parallel shaft axes from
their longest geometry edges for named screws/dowels. The axis is transformed
with its board. Unknown axes cause no independent displacement. In group/board
explosions, fittings follow their host and retract only axially relative to it.

Native exports read each node/panel origin and basis through `ToGlobal`; cabinet
montage is displayed in that cabinet's local frame. The MCP bounds preview lacks
basis vectors and records its orthogonal door-plane inference in `view_frame`.
Existing parent assemblies define the main groups when present. For a flat tree,
orientation groups are inferred and explicitly recorded in `presentation_groups`.
Exploded lineups and work orientations are display transforms only.

`--sample-module M1` produces all general overview pages but details only M1.
The native script defaults to the full model. `--layout steps` retains the previous
layout for comparison. `check_hierarchy.py` covers frames, camera projection,
unchanged source geometry and exploded spacing. Product photos are not integrated.

Run `\\RG\Bazis\Scripts\Export Asamblare.js` in BAZIS. A Windows Save As dialog
selects the PDF destination. Its default name is `Previzualizare montaj - YYYY-MM-DD HH-MM-SS.pdf`
(local Windows time). Each step has one positioning view: prior boards are seated,
all newly added boards are offset, and an arrow on each indicates the proposed
motion. Those instances are seated in the following step. The script reads the active model; it does not move,
hide, rebuild, rename, or save any model object. Running a standalone script may
end the MCP listener; restart ChatGPT MCP afterwards when needed.

The native script uses the existing private configuration's Python executable
and `Documents/BazisMCP/tools/assembly/export_assembly.py`. It writes a PDF and
a sibling `.assembly.json` containing the snapshot and proposed plan. No BLN is
generated; native drawing-sheet creation is not verified.

Composite fittings are detected using the documented `Block.IsFastener()`
method; descendants of those objects are never exported as furniture boards.
The atomic fitting record is retained in `report.hardware`. Plain fittings with
article codes or recognized fitting names are read too; drilling bodies and helper
lines are excluded. PAL/MDF/HDF/PFL/plywood boards from all cabinets are included,
even when BAZIS temporarily isolates one cabinet. No visibility flags are changed.
Repeated designations remain separate physical instances with numbered labels.

Line contours are extruded by panel thickness and transformed with `ToGlobal`.
Arcs and unsupported contours are explicitly marked as bounding-box illustrations.
Hardware geometry uses transformed extruded line/circle contours where available,
and component bounds for opaque CAD bodies. Composite children are drawn together
as one article. Fittings are counted once in module inventories and shown with
their host board. The host is chosen from native FindFastenedObjects links when
available, or bounds contact otherwise, selecting largest overlap for multi-board
joints. This attribution is provisional; unmatched fittings stay in the cabinet's
hardware and complete views. All fittings assigned to one board appear together
and move with that board in the positioning view. Each cabinet has a hardware
inventory/detail view and a completed view. A final global sheet uses the original
positions of every cabinet, preserving the room layout rather than re-packing.

Names are kept Unicode end-to-end. The MCP preview snapshot is transferred using
ASCII JSON escapes to avoid Windows codepage conversion. Demonstrable prior
UTF-8-as-cp1252 corruption is repaired before display; valid Unicode is preserved.

Machining/boolean results, holes, collision checks,
assembly stability and validated joint directions are not implemented.

Modules named M1, M2 etc. define per-module instructions. The initial proposed
sequence is first side, horizontal boards by height, other sides, other boards,
back, plinth, doors. Names and geometry are heuristics only; notably removable
shelves versus fixed shelves and sliding backs require manual plan review.
Directions are illustrative, not verified insertion paths. At the user's request,
the PDF omits instructional boilerplate, color legends and red diagnostic footers;
the sidecar retains draft status and geometry warnings. Assembly validation is pending.

For an edited plan, extract the `plan` object to a JSON file and run:

`python export_assembly.py --input snapshot.json --plan plan.json --output guide.pdf`

Repetition compression combines matching steps within one contiguous mounting
stage (same parent, role and offset), within the same immediate
parent, with matching exact BAZIS designation and insertion offset. Per-board
assembly wrappers are skipped to find the logical parent containing several
boards. The starting base is not compressed. Hole equivalence is not checked:
the user's designation is authoritative. The PDF draws all matching instances together,
each with its own arrow and number, and lists their numbers and quantity in the
header. At most 12 matching boards are shown per operation. The
expanded plan and full inventory retain every instance, including repeated ones.

The `--input` file must contain the `report` object, not the combined sidecar.
Each board ID must occur once; missing/duplicate instances are rejected.
The preview produced through MCP uses global component bounding boxes only and is distinct
from a verified native script run.

Official legacy API declarations:
https://github.com/BazisSoft/Scripts/blob/master/node_modules/@types/bazis/index.d.ts

Validation: `node tools/assembly/check_native.mjs` checks global transforms,
thickness extrusion, atomic composite fittings, hinge detection, links, unchanged
model and temporary-file cleanup. `check_hardware.py` covers Unicode repair and
unique fitting attribution; `check_repetitions.py` covers repeated boards.
Live native execution is pending the first run.
