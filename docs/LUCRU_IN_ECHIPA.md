# Contribuții și publicarea versiunilor

## Flux Git

1. Actualizează clona locală și verifică `git status` înainte de modificare.
2. Creează un branch separat pentru fiecare corecție sau funcționalitate.
3. Folosește date sintetice în teste și adresa GitHub noreply în metadatele commiturilor.
4. Rulează verificările relevante și inspectează PDF-urile când modifici grafica.
5. Scrie un titlu concret de commit și câteva propoziții despre problemă, soluție și verificare.
6. Trimite un pull request către `main`.

## Instalare separată de surse

GitHub și clona locală păstrează sursele; folderul de scripturi BAZIS conține versiunea instalată. Un push nu actualizează automat instalarea.

Înainte de publicarea unui pachet, păstrează o copie locală a versiunii instalate, verifică dependențele și hash-urile și evită actualizările simultane sau în timpul unui export. Configurațiile locale nu se copiază în repository.

## Revert

Folosește `git revert <commit>` pe un branch, verifică rezultatul și publică separat pachetul corectat. Nu folosi reset hard pentru a rescrie istoricul comun.

## Confidențialitate

Nu adăuga fișiere excluse cu `git add -f`. Modelele, bazele de date, exporturile, logo-urile și credențialele trebuie să rămână în afara surselor. `.gitignore` nu curăță retroactiv istoricul; verifică și commiturile înaintea publicării.
