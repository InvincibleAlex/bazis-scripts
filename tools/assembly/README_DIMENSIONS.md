# Export Cote

Rulează `Export Cote.js` în BAZIS și alege destinația PDF. Scriptul citește modelul fără să îl modifice și folosește terminalul separat pentru progres.

Fiecare placă este afișată dinspre +Z local, fără feronerie. Originea cotelor este Xmin/Ymin al conturului local. Sunt incluse dimensiunile generale, reperele găurilor și tabelul complet X/Y/Z, diametru, adâncime și față de intrare. Desenul limitează numărul cotelor de poziție pentru lizibilitate; tabelul păstrează toate găurile asociate nativ plăcii.

Frezările drepte cu profil dreptunghiular sunt cotate numai când amprenta se confirmă în geometria nativă: distanțe față de margini, început/final, lungime, lățime și adâncime. Alte profiluri sunt marcate pentru verificare. Decupajele din contur sunt desenate, dar segmentele lor nu sunt încă cotate individual. Plăcile curbe necesită vedere desfășurată și sunt refuzate explicit.

Lângă PDF se salvează un fișier `.cote.json` cu datele native folosite. `Export Asamblare` este independent.

Validare: `check_dimensions.py`, `check_dimensions_console.py`, `check_dimensions_native.mjs`; verificare vizuală PDF pe două plăci dintr-un export real existent.

Prezentare: vedere izometrică, explozii pe tronsoane/corpuri/subansambluri/plăci și inventar plăci, urmate de paginile cotate ale fiecărui corp. Numerotarea globală folosește aceeași ordine ca Export Asamblare. Tabelele compacte lasă desenul în prim-plan. Cotele aproape identice pe aceeași axă sunt grupate cu toleranță 0,01 mm; tabelul păstrează valorile native.
