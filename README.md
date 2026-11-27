# BAZIS Scripts

Surse și istoric pentru exporturile BAZIS Woodworker: **Cote**, **Asamblare**, **Tabele Cubis / Komodo / Holver**, editor de cartuș și integrarea MCP.

Proiect open source; configurațiile de calculator, credențialele, modelele clienților și exporturile nu fac parte din distribuția surselor.

## Ce găsești aici

| Director | Conținut |
|---|---|
| `bridge/` | Lansatoare JavaScript executate în BAZIS și listener MCP |
| `tools/assembly/` | Randare PDF, cote, vederi, explozii, inventar, cartuș și verificări PAIC |
| `tools/cubis/` | Exporturile pentru furnizori și gruparea/ordonarea pieselor |
| `tools/cartus_editor/` | Editor HTML offline și exemple generice de cartuș |
| `tools/portable_dimensions/` | Construirea pachetului Python portabil |
| `tools/portable_export/` | Pregătirea distribuției exportului de tabele |
| `integrations/bazis_mcp/` | Server MCP Python, documentație, installer și teste |
| `tests/` | Verificări suplimentare ale exporturilor și listenerului |
| `docs/ISTORIC_COMMITURI.md` | Fiecare commit istoric, cu titlu, explicație și fișiere relevante |
| `docs/LUCRU_IN_ECHIPA.md` | Clone, branch, commit, publicare și revenire |

## Starea versiunii

Au fost păstrate commiturile originale și importată separat versiunea Contributor instalată pe RG, până la **PAIC-08**. Candidatul PAIC-08.1 nu este publicat ca funcție activă. Importul provine din fișierele instalate, nu reconstituie fictiv commituri individuale pentru fiecare etapă a lui Contributor.

Funcțiile actuale includ patru vederi ortografice generale și pe modul, muchii ascunse eliminate, legendă și secțiuni de frezare, liste generale compacte, cartuș JSON și verificări tehnice ale prelucrărilor/codurilor repetate. Coperta folosește Comandă – Nume – Articol, fără cartuș; ultima vedere generală redundantă este eliminată.

## Instalare și distribuție

BAZIS execută lansatoarele din folderul partajat `\\RG\Bazis\Scripts`. Acest repository este sursa versionată, nu folderul de producție. Un commit/push nu modifică automat scripturile folosite de colegi.

- Export Cote: vezi `tools/portable_dimensions/README.md`; pachetul complet include runtime și biblioteci, construite separat.
- MCP: vezi `integrations/bazis_mcp/README.md`; configurația este creată pentru profilul local de instalator.
- Cartuș: folosește exemplele generice din editor; șablonul real, logo-ul și valorile personale rămân locale/în share.
- Tabele: șabloanele comerciale XLSX și configurația bazei de materiale nu sunt incluse.

**Nu copia sursele peste share în timpul unui export și nu publica un fișier vechi fără să preiei schimbările colegilor.**

## Verificări

Python Windows compatibil, cu dependențele exportului instalate sau din pachetul portabil:

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

La importul pentru GitHub: **112 teste Python**, verificările editorului și portabilității, plus **64 verificări MCP simulate** au trecut. Testele simulate nu certifică automat execuția pe modelul live BAZIS; pentru schimbări grafice se verifică și PDF-uri randate, iar pentru producție se păstrează verificarea nativă.

## Protecția datelor

`.gitignore` exclude runtime-uri, configurații, parole/certificate, modele, baze de date, PDF/XLSX/CSV, diagnostice și backupuri. Nu executa `git add -f` pentru asemenea fișiere. `.gitignore` nu șterge istoricul; acesta a fost verificat separat după tipare de secrete înainte de prima publicare. Metadatele Git păstrează autorii commiturilor istorice.

Documentația de predare din `docs/GHID_CHATGPT_RG_BAZIS.md` este o fotografie a contextului inițial; comportamentul actual și modificările Contributor sunt documentate în istoricul nou și în surse. Nu trata o descriere istorică drept specificație actuală.
