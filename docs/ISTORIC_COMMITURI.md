# Istoric explicat al commiturilor

Titlurile sunt cele reale din Git, iar istoricul nu a fost rescris. Detaliile de arie se bazează pe fișierele atinse; diff-ul rămâne sursa exactă. Importul Contributor este un snapshot al versiunii instalate, nu o reconstituire fictivă a etapelor lui.

## 09d79e0 — Snapshot assembly exporter before mounting-order correction
**Data:** 2026-11-18.

Actualizează teste și utilitare, documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `.gitignore`, `README.md`, `bridge/Export Asamblare.js`, `tools/assembly/README.md`, `tools/assembly/callouts.py`, `tools/assembly/check_callouts.py`, `tools/assembly/check_hardware.py` și alte 8 fișiere.

## 24ad344 — Order mounting by hierarchy, geometric orientation, numeric code and position
**Data:** 2026-11-18.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README.md`, `tools/assembly/check_order.py`, `tools/assembly/export_assembly.py`, `tools/assembly/hierarchical.py`.

## a61ef66 — Sweep board centers left to right in cabinet coordinates
**Data:** 2026-11-18.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README.md`, `tools/assembly/check_order.py`, `tools/assembly/export_assembly.py`.

## 0e1dd73 — Mount inner face boards before outer closure and show completed cabinet before explosion
**Data:** 2026-11-18.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README.md`, `tools/assembly/check_order.py`, `tools/assembly/export_assembly.py`, `tools/assembly/hierarchical.py`.

## 7fb2b30 — Snapshot MCP bridge before native fastener-hole reader
**Data:** 2026-11-19.

Actualizează MCP și protocol BAZIS, teste și utilitare.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/mock-bazis.cjs`, `tests/test_bridge.cjs`.

## 95af103 — Read native fastener hole definitions through MCP object snapshots
**Data:** 2026-11-19.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 231f9d8 — Prepare native panel-drilling query and verified-hole outline renderer
**Data:** 2026-11-19.

Actualizează MCP și protocol BAZIS, PDF, cote, vederi și asamblare.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`, `tools/assembly/check_holes.py`, `tools/assembly/export_assembly.py`, `tools/assembly/holes.py`.

## ce20973 — Export BAZIS-calculated panel holes and show drilled face during preparation
**Data:** 2026-11-19.

Actualizează PDF, cote, vederi și asamblare, documentația și regulile proiectului.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/README.md`, `tools/assembly/check_holes.py`, `tools/assembly/check_native.mjs`, `tools/assembly/hierarchical.py`.

## d272086 — Read native hardware parameters and edge geometry through MCP
**Data:** 2026-11-20.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 7af83c9 — Track current Cubis Komodo Holver export before dimension correction
**Data:** 2026-11-20.

Actualizează exporturile Cubis/Komodo/Holver.

**Fișiere:** `bridge/Export Cubis.js`.

## cc58e9a — Normalize sub-0.01 mm contour offsets before all table exports
**Data:** 2026-11-20.

Actualizează exporturile Cubis/Komodo/Holver, teste și utilitare.

**Fișiere:** `bridge/Export Cubis.js`, `tests/test_cubis_dimensions.cjs`.

## 72e853d — Track current table builders before layer export support
**Data:** 2026-11-20.

Actualizează exporturile Cubis/Komodo/Holver.

**Fișiere:** `tools/cubis/export_cubis.mjs`, `tools/cubis/export_holver.mjs`, `tools/cubis/export_komodo.mjs`.

## 3aec476 — Read native panel layers and export doubling rows directly below parent plates
**Data:** 2026-11-20.

Actualizează MCP și protocol BAZIS, exporturile Cubis/Komodo/Holver, teste și utilitare.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `bridge/Export Cubis.js`, `tests/test_bridge.cjs`, `tests/test_cubis_layers.mjs`, `tools/cubis/export_cubis.mjs`, `tools/cubis/export_holver.mjs`, `tools/cubis/export_komodo.mjs` și alte 1 fișiere.

## f381380 — Show assembly export progress in terminal and generate PDF outside BAZIS
**Data:** 2026-11-20.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/assembly_console.py`, `tools/assembly/check_console.py`, `tools/assembly/check_native.mjs`, `tools/assembly/export_assembly.py`, `tools/assembly/hierarchical.py`.

## b64692f — Keep native fitting curves when construction edges contain only one point
**Data:** 2026-11-20.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/check_native.mjs`, `tools/assembly/check_native_curves.mjs`.

## 2de3742 — Add preparation fitting names and insertion arrows to native bore mouths
**Data:** 2026-11-20.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_preparation_annotations.py`, `tools/assembly/hierarchical.py`, `tools/assembly/preparation_annotations.py`.

## 22cd74b — Compact board inventory and place numbered circle leaders outside the cabinet
**Data:** 2026-11-20.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_inventory_layout.py`, `tools/assembly/export_assembly.py`, `tools/assembly/inventory_layout.py`.

## b1253eb — Open and acknowledge progress terminal before save dialog or model access
**Data:** 2026-11-20.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/assembly_console.py`, `tools/assembly/check_console.py`, `tools/assembly/check_native.mjs`.

## 2191840 — Detach console stdio from BAZIS and foreground the save dialog
**Data:** 2026-11-20.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/check_native.mjs`.

## a479d75 — Yield native assembly extraction in small batches and avoid repeated fitting-wide host searches
**Data:** 2026-11-20.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/check_native.mjs`.

## 98bced4 — Track database material reader before portable deployment
**Data:** 2026-11-23.

Actualizează teste și utilitare.

**Fișiere:** `tools/read_material_designations.py`.

## 870723b — Run table exports from a shared portable runtime with per-user protected database credentials
**Data:** 2026-11-23.

Actualizează exporturile Cubis/Komodo/Holver, distribuția portabilă, teste și utilitare.

**Fișiere:** `bridge/Export Cubis.js`, `tests/test_portable_cubis.cjs`, `tools/cubis/export_cubis.mjs`, `tools/cubis/export_holver.mjs`, `tools/cubis/export_komodo.mjs`, `tools/cubis/group_rows.mjs`, `tools/portable_export/CITESTE.txt` și alte 5 fișiere.

## ffb21a7 — Use shared default database credentials without per-PC setup
**Data:** 2026-11-23.

Actualizează distribuția portabilă, teste și utilitare.

**Fișiere:** `tools/portable_export/CITESTE.txt`, `tools/read_material_designations.py`.

## 2d6591a — Show shared Cubis Komodo Holver export stages and errors in a visible terminal
**Data:** 2026-11-25.

Actualizează exporturile Cubis/Komodo/Holver, distribuția portabilă.

**Fișiere:** `bridge/Export Cubis.js`, `tests/test_portable_cubis.cjs`, `tools/portable_export/CITESTE.txt`, `tools/portable_export/progress_console.ps1`.

## e19b0d8 — Animate terminal loading and close either export console on any key after completion
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare, exporturile Cubis/Komodo/Holver, distribuția portabilă.

**Fișiere:** `bridge/Export Asamblare.js`, `bridge/Export Cubis.js`, `tools/assembly/assembly_console.py`, `tools/assembly/check_console.py`, `tools/portable_export/progress_console.ps1`.

## fc3c7d9 — Track native template preservation before sizing piece inputs
**Data:** 2026-11-25.

Actualizează exporturile Cubis/Komodo/Holver.

**Fișiere:** `tools/cubis/preserve_template.py`.

## 85ff73a — Size exported piece input rows and columns with single-line observations
**Data:** 2026-11-25.

Actualizează teste și utilitare, exporturile Cubis/Komodo/Holver.

**Fișiere:** `tests/test_piece_sizing.py`, `tools/cubis/export_cubis.mjs`, `tools/cubis/export_holver.mjs`, `tools/cubis/export_komodo.mjs`, `tools/cubis/preserve_template.py`, `tools/cubis/size_piece_inputs.py`.

## 3a7b560 — Fix Excel style child order and preserve header column widths in form templates
**Data:** 2026-11-25.

Actualizează teste și utilitare, exporturile Cubis/Komodo/Holver.

**Fișiere:** `tests/test_piece_sizing.py`, `tools/cubis/export_holver.mjs`, `tools/cubis/export_komodo.mjs`, `tools/cubis/preserve_template.py`, `tools/cubis/size_piece_inputs.py`.

## f5c447a — Show stage-based percentage bars with a right-hand spinner in both export consoles
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare, distribuția portabilă.

**Fișiere:** `tools/assembly/assembly_console.py`, `tools/assembly/check_console.py`, `tools/portable_export/progress_console.ps1`.

## 4a1c765 — Contain Holver observations and size Komodo piece columns without wrapping
**Data:** 2026-11-25.

Actualizează teste și utilitare, exporturile Cubis/Komodo/Holver.

**Fișiere:** `tests/test_piece_sizing.py`, `tools/cubis/export_holver.mjs`, `tools/cubis/export_komodo.mjs`, `tools/cubis/preserve_template.py`, `tools/cubis/size_piece_inputs.py`.

## 8c876d3 — Read native panel edge band properties and contour association through MCP
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## b06b4b4 — Expose native panel contours and local/global coordinate transforms in MCP
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## d3df1e3 — Expose native grain texture metadata and inspect solid mesh availability
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 090e8db — Expose native panel cut parameters trajectories and tool sections through MCP
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 593e500 — Inspect inherited native surface interfaces without executing geometry methods
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 111df7e — Avoid evaluating arbitrary mesh accessors during surface inspection
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`.

## 164f59b — Read native contour hierarchy and expose drilling-backed fastener panel links
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 37975f0 — Probe native hardware tessellation rebuild on detached temporary copies
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 59b9133 — Extend detached hardware surface probe with native FillElements stage
**Data:** 2026-11-25.

Actualizează MCP și protocol BAZIS.

**Fișiere:** `bridge/Codex_Bazis_Bridge.js`, `tests/test_bridge.cjs`.

## 8a12197 — Inspect native furniture source streams and document shared mesh versus parametric storage
**Data:** 2026-11-25.

Actualizează teste și utilitare, documentația și regulile proiectului.

**Fișiere:** `tests/test_furniture_source.py`, `tools/FURNITURE_SOURCE_FINDINGS.md`, `tools/inspect_furniture_source.py`.

## a5eaac2 — Prepare read-only VRML inventory for native hardware export experiment
**Data:** 2026-11-25.

Actualizează teste și utilitare.

**Fișiere:** `tests/test_vrml_export.py`, `tools/inspect_vrml_export.py`.

## 2364fe5 — Reuse assembly instructions for verified identical modules with page and panel references
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare, documentația și regulile proiectului.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/README.md`, `tools/assembly/check_module_repetitions.py`, `tools/assembly/hierarchical.py`, `tools/assembly/module_repetitions.py`.

## 809323a — Number hardware consistently and render dashed insertion axes with short arrows
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_preparation_annotations.py`, `tools/assembly/export_assembly.py`, `tools/assembly/hardware_labels.py`, `tools/assembly/hierarchical.py`, `tools/assembly/inventory_layout.py`, `tools/assembly/preparation_annotations.py`.

## b665676 — Add separate native board dimension PDF export
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare, documentația și regulile proiectului.

**Fișiere:** `bridge/Export Cote.js`, `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimensions.py`, `tools/assembly/check_dimensions_console.py`, `tools/assembly/check_dimensions_native.mjs`, `tools/assembly/dimensions_console.py`, `tools/assembly/export_dimensions.py`.

## 8ef7331 — Integrate dimension sheets with assembly hierarchy and colored milling dimensions
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare, documentația și regulile proiectului.

**Fișiere:** `bridge/Export Cote.js`, `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimensions.py`, `tools/assembly/check_dimensions_native.mjs`, `tools/assembly/export_assembly.py`, `tools/assembly/export_dimensions.py`, `tools/assembly/hierarchical.py` și alte 1 fișiere.

## 86d2c38 — Add two-sided colored board dimension sheets, banding and native grain indicators
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare, documentația și regulile proiectului.

**Fișiere:** `bridge/Export Cote.js`, `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimension_sheets.py`, `tools/assembly/check_dimensions.py`, `tools/assembly/check_dimensions_native.mjs`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## 6900857 — Use circled numeric banding references with arrows to native edges
**Data:** 2026-11-25.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/dimension_sheets.py`.

## 1b5deb5 — Restore complete parallel dimensions from shared origin and reduce sheet headings
**Data:** 2026-11-25.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_sheets.py`.

## cf45388 — Use thin sheet lines and content-sized compact tables
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## e37897c — Round board dimensions safely, avoid annotation collisions and omit empty opposite views
**Data:** 2026-11-25.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_annotations.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## 83296bf — Orient two-sided dimension sheets with long board edge horizontal
**Data:** 2026-11-25.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_sheets.py`.

## 853c3f3 — Add dimensioned A-A groove sections at top right and right-align coordinate tables
**Data:** 2026-11-25.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimension_sections.py`, `tools/assembly/dimension_sections.py`, `tools/assembly/dimension_sheets.py`.

## 27aeaad — Remove explanatory footer from dimension sheets
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/dimension_sheets.py`.

## 5f4c24b — Dimension each straight side of irregular polygon openings with interior placement when possible
**Data:** 2026-11-25.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_sheets.py`.

## 9eef3c4 — Place section markers along grooves clear of dimensions and neighboring sections
**Data:** 2026-11-25.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimension_sections.py`, `tools/assembly/dimension_annotations.py`, `tools/assembly/dimension_sections.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## b60e8f5 — Fit dimension sheets with nearest-edge rails, complete tables and type-based band labels
**Data:** 2026-11-25.

Actualizează documentația și regulile proiectului, PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/check_dimension_sections.py`, `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_page_layout.py`, `tools/assembly/dimension_sheets.py`.

## 13acba8 — Make Export Cote portable with shared bundled Python and self-contained renderer dependencies
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare, documentația și regulile proiectului, distribuția portabilă.

**Fișiere:** `bridge/Export Cote.js`, `tools/assembly/README_DIMENSIONS.md`, `tools/assembly/assembly_fonts.py`, `tools/assembly/check_dimensions_portable.mjs`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_assembly.py`, `tools/assembly/hierarchical.py` și alte 2 fișiere.

## 51489d1 — Center shared-coordinate markers beneath rotated dimension labels
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/dimension_annotations.py`, `tools/assembly/dimension_page_layout.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## c96b19f — Clean micron coordinate noise and show opposite-face machining as hidden geometry
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## 245c0b2 — Dimension contour shoulders and prioritize contour color on shared coordinates
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/dimension_page_layout.py`, `tools/assembly/dimension_sheets.py`.

## aa874ee — Match hole label leader stroke to its drilling color
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/dimension_sheets.py`.

## e61a497 — Avoid stray relocation leaders through dimension values
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/dimension_annotations.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## 2732792 — Normalize two-micron coordinate drift in dimension display
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## bcb2eb6 — Use contour chain for symmetric interrupted sides without redundant cumulative dimensions
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/dimension_page_layout.py`.

## 71abb0c — Place contour chains on the side of the notch opening
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/dimension_page_layout.py`.

## f041afe — Reuse transformed contour edges and verify rotated notch chains
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/dimension_page_layout.py`.

## 82950d8 — Unify dimension display rounding to hundredths with half-up rule
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## 13b24a3 — Merge opposite coordinate dimensions and anchor secondary marks beyond main rail
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/dimension_annotations.py`, `tools/assembly/dimension_page_layout.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/export_dimensions.py`.

## a2a3bf2 — Use single black contour chain rail with outer overall dimensions
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/dimension_page_layout.py`, `tools/assembly/dimension_sheets.py`.

## d4241bc — Include native worktop panels in Cubis export alongside PAL
**Data:** 2026-11-26.

Actualizează exporturile Cubis/Komodo/Holver, teste și utilitare.

**Fișiere:** `bridge/Export Cubis.js`, `tests/test_cubis_worktops.cjs`, `tools/cubis/export_cubis.mjs`.

## 28258b2 — Add offline HTML title-block editor with custom parameters and millimeter margins
**Data:** 2026-11-26.

Actualizează editorul HTML și celulele cartușului.

**Fișiere:** `tools/cartus_editor/CITESTE.txt`, `tools/cartus_editor/Editor cartus.html`, `tools/cartus_editor/cartus-initial.json`, `tools/cartus_editor/check_editor.cjs`, `tools/cartus_editor/editor.js`.

## 2faf3a4 — Decode BAZIS material lookup JSON as UTF-8 on Windows pipes
**Data:** 2026-11-26.

Actualizează teste și utilitare.

**Fișiere:** `tests/test_material_reader_encoding.py`, `tools/read_material_designations.py`.

## 5838c9e — Add merged grid cells, multirow logo layouts and undo to HTML title-block editor
**Data:** 2026-11-26.

Actualizează editorul HTML și celulele cartușului.

**Fișiere:** `tools/cartus_editor/CITESTE.txt`, `tools/cartus_editor/Editor cartus.html`, `tools/cartus_editor/cartus-logo-3-randuri.json`, `tools/cartus_editor/check_editor.cjs`, `tools/cartus_editor/check_ui.cjs`, `tools/cartus_editor/editor.js`.

## e934202 — Fit title-block logo to maximum cell area and reserve optional caption space
**Data:** 2026-11-26.

Actualizează editorul HTML și celulele cartușului.

**Fișiere:** `tools/cartus_editor/Editor cartus.html`, `tools/cartus_editor/cartus-logo-3-randuri.json`, `tools/cartus_editor/check_editor.cjs`, `tools/cartus_editor/editor.js`.

## 6f48d95 — Remove table JSON and CSV diagnostics only after all verified exports succeed
**Data:** 2026-11-26.

Actualizează exporturile Cubis/Komodo/Holver, teste și utilitare.

**Fișiere:** `bridge/Export Cubis.js`, `tests/test_table_diagnostic_cleanup.cjs`.

## 0b6650a — Clean successful PDF jobs and refine dimension hatching, spacing and opacity
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare, distribuția portabilă.

**Fișiere:** `bridge/Export Asamblare.js`, `tools/assembly/assembly_console.py`, `tools/assembly/check_console.py`, `tools/assembly/check_dimension_finishing.py`, `tools/assembly/check_dimensions_console.py`, `tools/assembly/dimension_annotations.py`, `tools/assembly/dimension_sheets.py` și alte 3 fișiere.

## 76e978c — Frame unchanged dimension layouts with live JSON cartouche and CCW landscape rotation
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare, editorul HTML și celulele cartușului, distribuția portabilă.

**Fișiere:** `tools/assembly/check_titleblock.py`, `tools/assembly/export_dimensions.py`, `tools/assembly/hierarchical.py`, `tools/assembly/titleblock.py`, `tools/cartus_editor/LEGARE_PARAMETRI_COTE.txt`, `tools/portable_dimensions/build_package.py`.

## a9931cf — Use shared natural ascending piece-code ordering in all supplier table exports
**Data:** 2026-11-26.

Actualizează teste și utilitare, exporturile Cubis/Komodo/Holver.

**Fișiere:** `tests/test_table_code_order.mjs`, `tools/cubis/export_cubis.mjs`, `tools/cubis/group_rows.mjs`.

## 2fb410c — Bind separate piece fields, native BAZIS order name and live external cartouche logo
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare, editorul HTML și celulele cartușului, distribuția portabilă.

**Fișiere:** `bridge/Export Cote.js`, `tools/assembly/check_dimensions_order.mjs`, `tools/assembly/check_titleblock.py`, `tools/assembly/titleblock.py`, `tools/cartus_editor/LEGARE_PARAMETRI_COTE.txt`, `tools/portable_dimensions/build_package.py`.

## 97b9062 — Record unified title-block and content editor settings TODO
**Data:** 2026-11-26.

Actualizează documentația și regulile proiectului.

**Fișiere:** `to do.md`.

## e65dde9 — Prepend paginated board edging and hardware specifications to dimension PDF
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_specification.py`, `tools/assembly/export_dimensions.py`, `tools/assembly/specification.py`, `tools/assembly/titleblock.py`.

## 0c97c3b — Compact specification rows with single line text and edging positions only
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_specification.py`, `tools/assembly/specification.py`.

## 286eda2 — Embed table titles in spanning header rows
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_dimension_page_layout.py`, `tools/assembly/check_dimension_sheets.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/specification.py`.

## ae72019 — Place specification tables immediately after isometric overview
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_specification.py`, `tools/assembly/export_dimensions.py`, `tools/assembly/specification.py`.

## c985316 — Resolve Romanian diacritics in cartouche quantity parameters
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_titleblock.py`, `tools/assembly/titleblock.py`.

## 27e7596 — Add aligned orthographic model views with overall dimensions after overview
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_model_views.py`, `tools/assembly/export_dimensions.py`, `tools/assembly/model_views.py`.

## 1c47f80 — Add colour legend and native project milling section catalogue
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_project_legend.py`, `tools/assembly/export_dimensions.py`, `tools/assembly/project_legend.py`.

## ed61df0 — Repair malformed quantity token in editor and tolerate colon in PDF parameters
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare, editorul HTML și celulele cartușului.

**Fișiere:** `tools/assembly/check_titleblock.py`, `tools/assembly/titleblock.py`, `tools/cartus_editor/check_editor.cjs`, `tools/cartus_editor/editor.js`.

## 108f6dc — Use common milling scale coloured legend and upright portrait furniture cover
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_project_legend.py`, `tools/assembly/dimension_sections.py`, `tools/assembly/hierarchical.py`, `tools/assembly/project_legend.py`.

## a87365a — Explain hatched through cutouts in project legend
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/project_legend.py`.

## 02f929e — Use native BAZIS product name for furniture cover title
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `bridge/Export Cote.js`, `tools/assembly/check_dimensions_order.mjs`, `tools/assembly/hierarchical.py`.

## 17f8c55 — Add per-module orthographic sheets after explosions and hide occluded edges
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_model_views.py`, `tools/assembly/hierarchical.py`, `tools/assembly/model_views.py`, `tools/assembly/visibility.py`.

## cb7a484 — Fit four overall model views with automatic group rotation
**Data:** 2026-11-26.

Actualizează PDF, cote, vederi și asamblare.

**Fișiere:** `tools/assembly/check_model_views.py`, `tools/assembly/model_views.py`.

## c576aef — Document complete BAZIS RG handoff workflow and MCP tool schemas
**Data:** 2026-11-26.

Actualizează documentația și regulile proiectului.

**Fișiere:** `docs/ANEXA_MCP_BAZIS_SCHEME.md`, `docs/GHID_CHATGPT_RG_BAZIS.md`.

## f99f368 — Integreaza versiunea Contributor instalata pe RG: PAIC-01–08
**Data:** 2026-11-27.

Preia sursele curente din share, inclusiv validarea codurilor repetate, decupajele tehnologice, frezarile la 45 de grade, corectiile cantitatilor, vizibilitatea si etichetele. Include consolidarea prelucrarilor si protectia exportului atomic. PAIC-08.1 ramane candidat neinstalat conform jurnalului Contributor. Nu modifica pachetul de productie; sincronizeaza numai sursele locale pentru publicare. Verificare initiala: suita locala veche are trei incompatibilitati cu noul comportament, documentate pentru actualizarea testelor in commit separat.

**Fișiere:** `bridge/Export Cote.js`, `tools/assembly/bevel_sections.py`, `tools/assembly/dimension_annotations.py`, `tools/assembly/dimension_page_layout.py`, `tools/assembly/dimension_sections.py`, `tools/assembly/dimension_sheets.py`, `tools/assembly/dimensions_console.py` și alte 11 fișiere.

## ac06455 — Pregateste sursele MCP, exclude datele private si actualizeaza testele
**Data:** 2026-11-27.

Include serverul MCP Python, listenerul, probele, documentatia si testele din proiectul local, fara configuratii sau runtime-uri. Extinde gitignore pentru baze de date, modele, exporturi, diagnostice, logo, date per utilizator si dependente generate. Actualizeaza mock-ul confirmarii PDF si asteptarile cartusului conform comportamentului instalat de Contributor; 112 teste Python si verificarile editorului/portabilitatii trec.

**Fișiere:** `.gitignore`, `integrations/bazis_mcp/CHANGELOG.md`, `integrations/bazis_mcp/LICENSE`, `integrations/bazis_mcp/README.md`, `integrations/bazis_mcp/bazis_mcp/__init__.py`, `integrations/bazis_mcp/bazis_mcp/server.py`, `integrations/bazis_mcp/bazis_mcp/settings.py` și alte 22 fișiere.
