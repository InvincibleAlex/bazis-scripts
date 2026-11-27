# Pornire pe calculatorul configurat

Serverul MCP se numește **bazis**. Proiectul este în `Documents\BazisMCP`.

1. Deschide BAZIS și proiectul pe care vrei să lucrezi.
2. Intră în **Scripts → Script editor** și deschide
   `Documents\Bazis\Scripts\Codex_Bazis_Bridge.js`.
3. Apasă **Run / F5**. Lasă scriptul activ. Bara de informații arată
   „Codex MCP activ. Oprire: `.”, fără verificarea repetată a prezenței MCP.
   Nu trebuie să rulezi din nou diagnosticul.
4. Reîncarcă serverele MCP sau repornește aplicația Codex pentru a încărca
   serverul **bazis**, adăugat de instalator.
5. Cere: „Verifică bazis_status și bazis_ping, apoi citește corpurile din model”.

În versiunea 0.2.1, Escape este interceptat de script pentru a evita oprirea accidentală.
Oprirea este configurată pe tasta de sub Escape, cea cu grav/backtick și tilde
(VK_OEM_3=192). Poți opri și prin MCP sau comanda explicită Stop din editor.
Unele comenzi manuale BAZIS pot încheia scriptul; îl pornești din nou cu F5.

La prima pornire a versiunii 0.2.1, apasă Escape în vederea 3D și verifică dacă mesajul
rămâne afișat. Contorul `escape_protection.ignored_events` permite confirmarea interceptării
prin MCP. Compatibilitatea evenimentelor de tastatură trebuie confirmată în aplicația reală.
Testează apoi tasta de sub Escape: trebuie să oprească scriptul. Starea `stop_key.events`
permite verificarea opririi. Scriptul oprit rămâne oprit până la o nouă pornire manuală.

Indicatorul conectat/deconectat și semnalul periodic de prezență introduse anterior
au fost eliminate în 0.2.1. Rămân doar verificarea cozii comenzilor primite și
starea locală a listener-ului. Nu se caută aplicații/servere și nu se relansează scriptul.
După actualizare reîncarcă MCP-ul **bazis**, redeschide scriptul de pe disc în
editorul BAZIS și pornește-l cu F5.

Datele de comunicare sunt în `%USERPROFILE%\.bazis-mcp\runtime`.
Fișierele B3D salvate explicit de MCP sunt în subfolderul `exports`.
Modelul original nu este salvat automat de comenzile de editare.

Primul test real trebuie să citească modelul și selecția. Funcțiile de editare
au teste pe un model simulat; validarea lor în BAZIS se face pe un model de probă.

Pentru GitHub se publică sursele din `BazisMCP`, nu folderul `.bazis-mcp`
cu configurația și datele locale. Instalatorul păstrează copii ale configurației
Codex înainte de a o modifica. Detaliile sunt în README.md.

## Setări — server 0.2.0

Reîncarcă MCP-ul pentru a vedea cele 25 de instrumente. Listener-ul BAZIS 0.1.2
poate fi păstrat. Noile instrumente `bazis_settings_*` citesc configurațiile
salvate, independent de listener. Pot pregăti modificări într-o copie privată și
pot aplica/reveni la original doar cu aplicațiile BAZIS închise. Nicio aplicație
nu este închisă automat și nicio modificare nu este aplicată prin simpla citire.

Controlul bifelor dintr-un dialog deschis este o funcție separată, încă de
validat. Configurațiile salvate pot diferi de opțiunile nesalvate din dialog.
Detalii: [adaptorul de setări](SETTINGS.md).
