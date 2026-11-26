# Export Cote portabil

Pachetul Windows x64 se publică în `\\RG\Bazis\Scripts\Export Cote`, lângă `Export Cote.js`. Lansatorul caută mai întâi folderul de lângă script și apoi folderul comun. Se poate copia perechea script + folder în altă locație, inclusiv pe un alt calculator.

Nu folosește `.bazis-mcp/material-db-reader.json`, `Documents/BazisMCP`, Python sau biblioteci instalate în profilul utilizatorului. Nu conține configurarea bazei de materiale. Python, biblioteca standard, ReportLab, pypdf, NumPy, Pillow și charset-normalizer sunt incluse. `_pth` folosește numai căi relative în pachet, inclusiv directorul modulelor exportului; ignoră configurația Python a calculatorului gazdă.

Configurarea obligatorie per utilizator a fost eliminată. `runtime.json` este un inventar al versiunilor și modulelor, nu un fișier obligatoriu pentru pornire. Dacă o copie locală este incompletă, lansatorul încearcă pachetul complet din partajare. Dacă nu există niciun pachet complet, enumeră fișierele lipsă; nu creează module goale în locul generatorului.

Construire: rulează `build_package.py --destination <folder> --python-runtime <runtime Windows x64>`, cu un Python Windows x64 de aceeași versiune major/minor. Instrumentul copiază biblioteca standard și distribuțiile instalate ale dependențelor cu licențele lor, fără configurația utilizatorului sau baza de date. Modulele locale sunt descoperite recursiv din importurile generatorului și consolei. Nu se instalează nimic pe calculatorul unde rulează exportul.

Verificare: `check_dimensions_portable.mjs` simulează alt profil Windows, cale locală cu spații, configurare absentă și fallback dintr-un pachet incomplet. S-a executat și generatorul real cu Python-ul inclus și un mediu USERPROFILE/PYTHONHOME/PYTHONPATH fără instalare locală.
