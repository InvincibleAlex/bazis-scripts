# Lucru în echipă — Contributor și Contributor

## Surse, GitHub și producție sunt trei lucruri diferite

1. Fiecare calculator are propria clonă Git locală.
2. GitHub păstrează istoricul comun și branch-urile.
3. Folderul partajat BAZIS conține versiunea instalată pentru utilizatori.

Modificarea din share nu apare automat în clone sau pe GitHub; commitul/push-ul nu publică automat în share. Repository-ul nu instalează dependențe sau configurări personale.

## Flux recomandat

- Înainte de editare: `git status`, `git fetch origin`, apoi actualizează branch-ul fără să pierzi lucrul necomis.
- Creează branch pentru sarcină: `git switch -c fix/descriere` sau `feature/descriere`.
- Fiecare își configurează identitatea locală cu numele propriu și adresa GitHub noreply.
- Modifică sursele; rulează testele relevante și verifică PDF-ul când schimbi grafica.
- Commitul are titlu concret și un corp de câteva propoziții: problema, comportamentul final și verificarea.
- Fă push pe branch și pull request către `main`, cu același rezumat.
- După integrare, persoana care publică face backupul versiunii instalate și copiază doar fișierele necesare.
- Recalculează hash-urile manifestului pentru helper-ele publicate și verifică sursă versus destinație.
- Notează versiunea/commitul publicat în jurnalul echipei; nu rula două publicări simultane.

Nu edita același fișier direct în share de pe două PC-uri. Dacă o intervenție urgentă se face acolo, importă imediat schimbarea în repo într-un commit identificabil, înainte de următoarea publicare.

## Exemplu de commit

```text
Corectează cantitatea din cartuș pentru coduri repetate

Numără instanțele fizice desenate pe planșă în locul totalului după cod.
Păstrează separarea pieselor cu prelucrări diferite și numerele paginilor.
Verificare: teste pentru una/două/trei instanțe și comparație PDF.
```

## Revert

Folosește `git revert <commit>` pe un branch, verifică, integrează și publică din nou fișierele rezultate. Nu folosi reset hard pe istoric comun și nu presupune că revertul modifică singur pachetul instalat.

## Ce nu se publică

Configurații `%USERPROFILE%/.bazis-mcp`, runtime.json de calculator, Parametri_cote.json, șablonul personal, logo, parole Firebird, modele B3D/BLN, baze de date, exporturi ale clienților și backupuri. Adaugă numai exemple generice, fără date de producție. Nu activa CI/deployment automat către LAN până când echipa nu stabilește explicit mecanismul.
