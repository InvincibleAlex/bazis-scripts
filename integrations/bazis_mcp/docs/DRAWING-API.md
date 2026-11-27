# Native drawing API investigation

The requested workflow is native BAZIS processing before PDF export. It must
control hole-label placement/size, extension-line presentation and cutting-section
scale. The saved-profile adapter and 3D model tools do not prove access to these
2D drawing objects or to the generation/rendering pipeline.

Primary local references are the installation's `Manual/en/Drawings.pdf` and
`Manual/en/Script.pdf`. The latter describes Contour2D for geometry and SVG contour
import/export. This is not equivalent to an editable sheet with text/dimensions.
The official [legacy declarations](https://github.com/BazisSoft/Scripts/blob/master/CHANGELOG.md)
also document `NewImportExport(): ImportExport` with an SVG contour adapter.

`Codex_Bazis_DrawingAPI_Probe.js` inspects metadata for `Action`, `Control`,
`Owner`, `system`, `IDrawingManager`, `TUserSettings` and drawing/export types.
It reads descriptors and prototype members without evaluating native getters or
invoking unknown methods/constructors. It constructs only the documented
NewImportExport wrapper and never calls Load/Save or any drawing-generation method.
Names and declared parameter counts are not proof of signatures or behavior.

The probe writes `Codex_Bazis_DrawingAPI.report.json` under the user's normal
Documents/Bazis/Scripts folder. This private report is excluded from releases.
Run it once in the BAZIS Script Editor. Running another script can end the active
MCP listener action; run Codex_Bazis_Bridge.js again afterward if needed. No MCP
reload is needed to run the standalone probe.

Native execution and useful 2D access are pending. The metadata-only behavior
is tested with a mock that fails on host-getter reads, drawing-method calls and
native settings constructor calls. No PDF postprocessor has been implemented.
