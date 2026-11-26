# Export Cote

Branch dedicat: `feature/export-cote`.

Rulează `Export Cote.js` în BAZIS și alege destinația PDF. Scriptul citește modelul fără să îl modifice; progresul apare în terminalul separat.

Vederile izometrice, exploziile pe tronsoane/corpuri/subansambluri/plăci și inventarul preced paginile cotate ale fiecărui corp. Numerele plăcilor folosesc aceeași ordine globală ca Export Asamblare.

Când ambele fețe au prelucrări proprii, foaia prezintă fața 1 (Zmax) sus și fața 2 (Zmin) jos. Dacă prelucrările sunt pe o singură față, se exportă numai acea vedere și tabelul ei. Găurile străpunse, găurile de cant, canturile și textura nu impun singure repetarea celeilalte fețe. O frezare cu față nativă neclasificată păstrează ambele vederi. Întoarcerea se face pe latura cea mai lungă: sus–jos pentru plăci late, stânga–dreapta pentru plăci înalte. X/Y sunt recalculate în fiecare vedere din colțul stânga jos; Z din tabel rămâne Z local nativ. Simbolul mic al originii este lipit de colțul stânga jos al tabelului și lipsește când tabelul este gol. Foile cu două fețe folosesc A3 peisaj, cu latura lungă a plăcii orizontal și fețele una sub alta. Plăcile native înalte sunt rotite în prezentare cu 90°; geometria, vectorii găurilor, canturile, frezările, textura și coordonatele X/Y din tabele folosesc aceeași transformare. Originea fiecărei vederi rămâne în stânga jos. Foile cu o singură față păstrează alegerea A3 portret/peisaj după orientarea nativă. Tabelele lungi se continuă în coloane alăturate pe aceeași foaie, fără repetarea desenelor și fără micșorarea fontului.

Culori: albastru pentru găuri de față, roșu pentru găuri străpunse și cote de contur, fuchsia pentru găuri de cant, maro pentru frezări. Străpungerea este verificată din poziția, direcția, adâncimea găurii și limitele Z native. Găurile de cant arată în plan diametrul și lungimea găuririi. Cotele repetate pe aceeași axă se grupează cu toleranță 0,01 mm; coordonatele native exacte rămân în tabel. La o coordonată comună mai multor tipuri, liniile mici suplimentare de lângă valoare păstrează culorile comune.

Frezările drepte cu profil dreptunghiular sunt cotate când amprenta este confirmată de geometria nativă. Cotele de poziție se opresc pe muchia prelucrată, nu pe axă. Lungimea, lățimea și adâncimea sunt păstrate. Celelalte profiluri apar prin traiectoria nativă. Listele de parametri ale frezării nu sunt afișate sub tabele.

Contururile închise sunt citite din Contour și arborele Contours/Children. Golurile sunt separate prin includere geometrică; se cotează dimensiunile interioare și distanțele X/Y către cele mai apropiate margini. Cercurile au diametrul cotat. Pentru golurile poligonale neregulate, fiecare latură dreaptă are cota lungimii reale; se preferă interiorul dacă textul încape. Plăcile curbate necesită desfășurata nativă.

Canturile folosesc ElemIndex nativ, cu repere numerice încercuite și săgeată către muchia căntuită și tabel cu nume, denumire și grosime originale. Direcția texturii folosește enumerația nativă Horizontal/Vertical și este reprezentată prin două linii paralele în centrul plăcii; pentru None nu se inventează o direcție.

Lângă PDF se salvează `.cote.json` cu raportul nativ și planul. Cartușul și orientarea personalizată sunt lăsate deoparte.

În vederile cotate, numărul plăcii apare în titlu, fără bulină centrală. Bulele din inventar sunt păstrate.

Cotele de poziție sunt cote paralele complete, fiecare pornind din același punct de origine, pe linii succesive spre exterior. Antetul temporar din stânga sus este redus la 6/5 pt.

Dimensiunile plăcii și cotele de contur sunt afișate cu maximum două zecimale, folosind rotunjire half-up (971,998 → 972). Găurile de găurire păstrează formatterul separat cu trei zecimale (200,75 → 200,75; 199,998 → 199,998); coordonatele native din raport nu se modifică. Golurile mici au cotele de dimensiune în exterior. Un sistem comun de amplasare evită suprapunerea textelor și repoziționează etichetele cu linii de legătură; nu omite etichete în zone aglomerate.

Secțiuni locale A–A: pentru canale drepte cu amprentă și profil dreptunghiular confirmate nativ se desenează marcajul în vederea feței prelucrate și un detaliu mic în dreapta sus. Detaliul este hașurat și cotat cu lățimea, adâncimea și grosimea plăcii; deschiderea este orientată în sus, cu lățimea cotată deasupra. Limitele locale ale materialului provin din intersecția conturului nativ cu planul secțiunii. Toate detaliile sunt așezate în grup în dreapta sus, pe aceeași foaie. Tabelele de coordonate sunt aliniate la dreapta, la 10 mm de marginea foii/cadrului; se așază sub detalii, fără să se suprapună.

Marcajele de secțiune sunt plasate după cote, etichete și reperele de cant. Se caută o poziție liberă de-a lungul canalului, cu verificarea întregului marcaj (linie, săgeți și litere) față de texte, liniile cotelor și celelalte secțiuni. Secțiunea nativă locală este recalculată în poziția aleasă; nu rămâne obligatoriu la mijlocul frezării.

Așezarea folosește 10 mm față de margini și între zonele majore: tabele, detalii și desenul cotat complet. Tabelul de canturi are baza la 10 mm de marginea de jos. Zona și scara desenelor se calculează după extinderea tuturor cotelor; fețele sunt aliniate și au scară comună maximă în spațiul disponibil. Cotele găurilor se plasează pe marginea apropiată (sus/jos pentru X, stânga/dreapta pentru Y), păstrând valorile coordonatelor din originea vederii. Cotele de gabarit sunt în exteriorul celorlalte cote. Spațierea dintre șine este 13 pt; marcajele culorilor comune sunt retrase de lângă cifre. Textele separate Face 1/Face 2 de lângă desene sunt eliminate.

Tipurile de cant primesc numere: toate muchiile cu același material, denumire, grosime și lățime au același număr încercuit și un singur rând în tabel. Tabelele goale nu sunt desenate, nici titlurile sau axele lor. Textul din tabele rămâne la dimensiunea stabilită; celulele lungi se împart pe rânduri, fără reducerea fontului. Se generează o singură foaie cotată pentru fiecare placă; dacă sunt necesare foarte multe coloane sau cote, dimensiunea foii crește în loc să repete placa ori să micșoreze textul.

Distribuție portabilă: Export Cote.js folosește folderul Export Cote de lângă script sau din partajarea comună, cu Python și bibliotecile incluse. Nu depinde de instalarea MCP ori de configurarea unui utilizator. Vezi ../portable_dimensions/README.md.
