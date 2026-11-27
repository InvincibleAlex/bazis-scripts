# BAZIS Scripts

Instrumente open source pentru automatizarea BAZIS Woodworker: export PDF cotat, documentație de asamblare, tabele pentru furnizori, editor de cartuș și integrare MCP.

## Funcționalități

- Export Cote: vederi ortografice, muchii vizibile, cote, găuri, decupaje, frezări și secțiuni.
- Export Asamblare: vederi izometrice, explozii pe module și inventar de plăci.
- Export Tabele: generatoare pentru formatele Cubis, Komodo și Holver.
- Cartuș configurabil prin JSON și editor HTML offline cu celule unite și parametri.
- Distribuție Windows prin pachete portabile și foldere partajate.
- Server MCP pentru inspectarea modelului, operații native limitate și setări salvate.

## Structură

| Director | Conținut |
|---|---|
| `bridge/` | Lansatoare JavaScript BAZIS și listener MCP |
| `tools/assembly/` | Generatoare PDF, geometrie, cote, cartuș și verificări |
| `tools/cubis/` | Exporturi de tabele |
| `tools/cartus_editor/` | Editor HTML și șabloane generice |
| `tools/portable_dimensions/` | Construirea pachetului Python portabil |
| `tools/portable_export/` | Distribuția exportului de tabele |
| `integrations/bazis_mcp/` | Server MCP, instalator și documentație |
| `tests/` | Teste și modele simulate |

## Instalare

BAZIS Woodworker și componentele sale native se instalează separat; nu sunt distribuite aici. Pentru MCP consultă `integrations/bazis_mcp/README.md`, iar pentru pachetul PDF `tools/portable_dimensions/README.md`.

Lansatoarele se folosesc împreună cu pachetele lor complete. Sursele nu includ interpretoarele, bibliotecile instalate sau șabloanele comerciale ale furnizorilor. Înainte de utilizare configurează căile șabloanelor și ale serverului de fișiere pentru mediul tău; unele adaptoare păstrează convențiile implementării inițiale.

Editorul HTML poate fi deschis local. Folosește exemplele generice și păstrează configurația, valorile personale și logo-ul în afara repository-ului.

## Specificația XML pentru Export Cote

Versiunea curentă cere o specificație XML nativă exportată manual din BAZIS pentru modelul integral. Salvează modelul `.b3d`, apoi regenerează XML-ul din aceeași versiune. Exportul caută specificația în directorul modelului sau în directorul de predare corespunzător; dacă alegerea este ambiguă, cere selectarea fișierului. Verifică identitatea comenzii/produsului, data, reperele și multiplicitățile și solicită confirmarea provenienței. XML-ul nu este generat automat de lansator.

## Dezvoltare și verificare

```powershell
python -m unittest discover -s tools/assembly -p 'check_*.py'
node tools/assembly/check_dimensions_order.mjs
node tools/assembly/check_dimensions_portable.mjs
node tools/cartus_editor/check_editor.cjs
node tools/cartus_editor/check_ui.cjs
node integrations/bazis_mcp/tests/test_bridge.cjs
node integrations/bazis_mcp/tests/test_drawing_probe.cjs
node integrations/bazis_mcp/tests/test_lifecycle_probe.cjs
```

Folosește un Python compatibil cu dependențele exportului. Verificările simulate nu înlocuiesc validarea în BAZIS și inspecția PDF-urilor înaintea utilizării în producție. Verifică geometria, materialele și prelucrările pe un model de test înaintea publicării unei versiuni instalate.

Vezi `docs/LUCRU_IN_ECHIPA.md` pentru branch-uri, commituri, actualizare și revert, respectiv `docs/ISTORIC_COMMITURI.md` pentru evoluția funcțională.

## Date și configurații

Nu publica modele ale clienților, baze de date, configurații locale, credențiale, logo-uri, exporturi sau diagnostice. Aceste categorii sunt excluse prin `.gitignore`. Exemplele și testele trebuie să utilizeze date sintetice.

## Licență

[MIT](LICENSE). Numele produselor și mărcile menționate aparțin deținătorilor lor; proiectul este independent și nu distribuie aplicația BAZIS.
