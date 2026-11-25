# Export Cote

Branch dedicat: `feature/export-cote`.

Rulează `Export Cote.js` în BAZIS și alege destinația PDF. Scriptul citește modelul fără să îl modifice; progresul apare în terminalul separat.

Vederile izometrice, exploziile pe tronsoane/corpuri/subansambluri/plăci și inventarul preced paginile cotate ale fiecărui corp. Numerele plăcilor folosesc aceeași ordine globală ca Export Asamblare.

Când ambele fețe au prelucrări proprii, foaia prezintă fața 1 (Zmax) sus și fața 2 (Zmin) jos. Dacă prelucrările sunt pe o singură față, se exportă numai acea vedere și tabelul ei. Găurile străpunse, găurile de cant, canturile și textura nu impun singure repetarea celeilalte fețe. O frezare cu față nativă neclasificată păstrează ambele vederi. Întoarcerea se face pe latura cea mai lungă: sus–jos pentru plăci late, stânga–dreapta pentru plăci înalte. X/Y sunt recalculate în fiecare vedere din colțul stânga jos; Z din tabel rămâne Z local nativ. Simbolul mic al originii apare numai sub fiecare tabel. Plăcile înalte folosesc A3 portret, cele late A3 peisaj. Tabelele lungi continuă pe foi care păstrează ambele vederi.

Culori: albastru pentru găuri de față, roșu pentru găuri străpunse și cote de contur, fuchsia pentru găuri de cant, maro pentru frezări. Străpungerea este verificată din poziția, direcția, adâncimea găurii și limitele Z native. Găurile de cant arată în plan diametrul și lungimea găuririi. Cotele repetate pe aceeași axă se grupează cu toleranță 0,01 mm; coordonatele native exacte rămân în tabel. La o coordonată comună mai multor tipuri, liniile mici suplimentare de lângă valoare păstrează culorile comune.

Frezările drepte cu profil dreptunghiular sunt cotate când amprenta este confirmată de geometria nativă. Cotele de poziție se opresc pe muchia prelucrată, nu pe axă. Lungimea, lățimea și adâncimea sunt păstrate. Celelalte profiluri apar prin traiectoria nativă. Listele de parametri ale frezării nu sunt afișate sub tabele.

Contururile închise sunt citite din Contour și arborele Contours/Children. Golurile sunt separate prin includere geometrică; se cotează dimensiunile interioare și distanțele X/Y către cele mai apropiate margini. Cercurile au diametrul cotat. Pentru forme poligonale, dimensiunile interioare sunt extinderea X/Y a golului. Plăcile curbate necesită desfășurata nativă.

Canturile folosesc ElemIndex nativ, cu repere numerice încercuite și săgeată către muchia căntuită și tabel cu nume, denumire și grosime originale. Direcția texturii folosește enumerația nativă Horizontal/Vertical și este reprezentată prin două linii paralele în centrul plăcii; pentru None nu se inventează o direcție.

Lângă PDF se salvează `.cote.json` cu raportul nativ și planul. Cartușul, orientarea personalizată și secțiunea/modelul de freză sunt lăsate deoparte.

În vederile cotate, numărul plăcii apare în titlu, fără bulină centrală. Bulele din inventar sunt păstrate.

Cotele de poziție sunt cote paralele complete, fiecare pornind din același punct de origine, pe linii succesive spre exterior. Antetul temporar din stânga sus este redus la 6/5 pt.

Dimensiunile plăcii și cotele de contur sunt afișate cu maximum două zecimale, folosind rotunjire half-up (971,998 → 972). Găurile de găurire păstrează formatterul separat cu trei zecimale (200,75 → 200,75; 199,998 → 199,998); coordonatele native din raport nu se modifică. Golurile mici au cotele de dimensiune în exterior. Un sistem comun de amplasare evită suprapunerea textelor și repoziționează etichetele cu linii de legătură; nu omite etichete în zone aglomerate.
