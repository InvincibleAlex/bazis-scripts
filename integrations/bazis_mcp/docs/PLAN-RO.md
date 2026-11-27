# Plan de extindere

Serverul 0.2.1 păstrează cele șase instrumente MCP pentru configurațiile salvate.
Listener-ul 0.2.1 pornește manual, cu indicator static și oprire de la tasta de sub Escape.

## Setări pentru generarea desenelor — prioritatea curentă

Profilul ales de utilizator pentru continuare este **EXPORT RG** (numit de
utilizator „Contributor”), din `00. Export RG.pdrw`, nu EXPORT Contributor. Formatul uzual
este A4. A fost pregătită separat o copie de probă cu tabelul coordonatelor
găurilor și legenda găurilor pe foaia a doua; originalul și configurația activă
au rămas intacte. Încărcarea copiei și rezultatul vizual nu sunt încă validate.
Urmează examinarea PDF-ului cu etichete suprapuse și desene prea mici, pe care
utilizatorul l-a furnizat ulterior. Exemplul a fost inspectat vizual: cifre roșii
foarte mici la găuri, două secțiuni de frezare mari, linii de cote care se confundă
cu geometria. Pagina PDF este Letter (612 x 792 pt), deși ținta utilizatorului este A4.

Utilizatorul a precizat explicit că soluția trebuie să lucreze în BAZIS înainte
de export, asupra generării sau a desenului nativ, nu să prelucreze PDF-ul final.
Nu a fost creat sau modificat niciun PDF. Se investighează API-ul pentru foi,
texte, cote, linii prelungitoare și secțiuni, folosind în primul rând manualele
instalate `Manual/en/Drawings.pdf` și `Manual/en/Script.pdf`. Prezența unor tipuri
precum `IDrawingManager` nu confirmă acces la motorul de desen.

Pregătit: `Codex_Bazis_DrawingAPI_Probe.js`, diagnostic de metadate care nu
invocă metodele de desen/configurare și nu citește getter-e native arbitrare.
Necesită o rulare manuală în BAZIS pentru verificarea interfețelor instalate.
Raportul se salvează lângă scripturile utilizatorului, în afara surselor publice.

- Implementat: inventarierea și căutarea setărilor salvate, cu identificatori
  și revizii. Citirea a 44 de fișiere locale a fost verificată.
- Implementat: pregătirea unei modificări într-o copie privată și afișarea diferenței.
- Implementat și testat pe fișiere temporare: aplicare și revenire, doar cu BAZIS
  închis, cu verificarea reviziei și copii ale originalului.
- Identificarea accesului nativ la setările din memorie ale aplicației.
- Validarea încărcării profilului în BAZIS și a efectului asupra unui desen de probă.
- Controlul ferestrelor/setărilor nesalvate: în verificare. BAZIS pornit ca
  administrator nu a expus ferestre controlabile sesiunii obișnuite.
- Cele patru configurații binare identificate necesită un adaptor separat.

Constatări din 16 octombrie 2026: fișierul local `CreateDrawings.xml`, cu
`Version=10`, conține profiluri `CreateDrawingsSet`. Secțiunea
`AssemblyOnDoors` corespunde setărilor pentru panouri frontale din captura
utilizatorului. Au fost identificate următoarele câmpuri:

| Câmp relativ | Interpretare de verificat în aplicație |
|---|---|
| `MakeAssemblies` | Crearea desenelor de asamblare |
| `ViewOffset` | Spațiul între vederi |
| `ShowCuts` | Secțiuni pe desen |
| `AutoTransformBlock` | Rotirea blocului în sistemul său de coordonate |
| `ModelViewParams/ShowGabaritSizes` | Cotele de gabarit |
| `ModelViewParams/DrawPanelsTextureDirection` | Orientarea texturii |
| `ModelViewParams/MakeObjectsBlocks` | Salvarea ca blocuri |
| `ModelViewParams/DrawMstb` | Scara foii |

Valorile citite din profilul salvat concordă cu opțiunile vizibile în captură.
Aceasta confirmă citirea configurației de pe disc, nu citirea sau modificarea
în timp real a dialogului deschis. Codificarea `SelectedViews` și a modurilor
numerice de afișare rămâne de verificat; nu se vor deduce valori pentru scriere.
Modificările nesalvate ale dialogului pot diferi de fișier. Înainte de scriere
trebuie stabilit cum se încarcă profilul și cum se evită suprascrierea sa de către
aplicația aflată în execuție. Adaptorul refuză scrierea cât timp BAZIS rulează.

## Cataloage — în plan

- Baza completă de materiale: grupuri, denumiri, coduri și dimensiuni.
- Catalogul de frezări/prelucrări.
- Sisteme parametrice de feronerie și parametrii lor.

Materialul activ și materialele obiectelor din model se citesc deja prin MCP.
Acest acces nu confirmă enumerarea catalogului complet. Se va distinge între
datele citite prin API-ul BAZIS, configurațiile salvate și accesul direct la baza
de date; sursa și actualitatea vor fi indicate în rezultate.
