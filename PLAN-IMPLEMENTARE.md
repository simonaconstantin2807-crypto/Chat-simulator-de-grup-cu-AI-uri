# Plan de implementare — Consiliul CoSiMa

Pentru Claude Code. Etapele descriu **ce trebuie să funcționeze**, nu **cum** — stack-ul,
structura fișierelor și arhitectura rămân la latitudinea ta, alese potrivit pentru un chat de
grup cu 5 personaje AI, fără cont/login, fără RAG, fără tool calling (vezi `SPEC.md`).

Citește, în ordine: `SPEC.md`, cele 5 fișiere `personaj-*.md`, apoi `concept-aplicatie-miyuki.md`
(document de fundal — subiectul pe care personajele îl dezbat, nu funcționalitate de construit).
Folderul `arhiva/` conține versiuni înlocuite — nu e sursă de adevăr, nu se citește.

## Stack — deliberat nedecis

Nu e o omisiune, e abordarea cursului: în Partea 2 mergem pe vibe coding, cu spec minimal, iar
design-ul, structura codului și detaliile rămân la latitudinea lui Claude (sesiunea 7, slide 24).

Ce se știe despre direcție:

- **Modelul** se alege în sesiunea 8, unde instalăm Ollama și testăm system prompt-urile pe
  modele locale. Până atunci, orice model accesibil e bun pentru M0–M4 (prompturile au fost deja
  validate pe Gemini, în Google AI Studio).
- **Temperatura e per personaj**, nu globală — valorile recomandate sunt în fiecare
  `personaj-*.md` (0.3 la Operatoarea, 0.8 la Clienta). Cursul încurajează explicit asta.
- **Personajele sunt definite într-un fișier JSON de configurare** (`personaje.json`), nu
  hardcodate în cod — fiecare intrare are id, nume, avatar, culoare, temperatura recomandată și
  system prompt. Fișierele `personaj-*.md` rămân sursa de conținut pentru system prompt-uri,
  nu formatul de rulare.
- Rularea trebuie să pornească într-un pas, sau doi dacă backend și frontend sunt separate.

## Decizii de design lăsate implementatorului

Trei întrebări la care planul nu răspunde intenționat, dar care trebuie rezolvate până la M5-M6
(primele două sunt chiar întrebările ridicate în sesiunea 7, slide 19):

1. **Cât din istoric primește fiecare personaj?** Tot, sau doar o fereastră de ultimele N mesaje?
   Contează practic: cu cât promptul e mai lung, cu atât primul token întârzie mai mult — la o
   conversație de 100 de mesaje pe un model local, așteptarea devine jenantă.
2. **Ce vede un personaj din replicile celorlalți?** Trebuie să le vadă (definiția de „gata" nr. 4
   cere ca un personaj să comenteze ce a zis altul), dar rămâne de decis cum sunt marcate în
   context, astfel încât personajul să nu confunde vocea altcuiva cu a lui.
3. **Curățarea output-ului.** Prompturile spun „NU pui numele tău la început", dar modelele mici
   încalcă regula. Prefixul de tip `Maestra:` trebuie tăiat **înainte** de a ajunge pe ecran, nu
   după — altfel, cu streaming, se vede apărând și dispărând.

## M0 — Mediul pornește

Un prim mesaj trimis către un model AI și un răspuns primit, cât mai simplu posibil (un script
sau un test minimal). Fără asta, restul n-are sens.

## M1 — Serverul respiră

Un server care servește o pagină de chat goală și confirmă că poate vorbi cu modelul AI ales.

## M2 — Scheletul vizual

Interfață de chat de grup: header, listă de mesaje (hardcodate, ca să vadă cum arată), casetă
de input. Arată bine, nu face nimic încă.

## M3 — Un personaj, un răspuns

Trimit un mesaj, **un singur personaj** (ex. Maestra) răspunde, fără streaming. Mesajul apare
întreg, dintr-o bucată.

## M4 — Streaming

Răspunsul apare token cu token, cu indicator de „scrie..." înainte de primul cuvânt. Ăsta e
efectul „wow" al proiectului.

## M5 — Toate 5 personaje + orchestrare pe mențiuni (provizorie)

Toate personajele din `personaje.json` sunt disponibile. Dacă mesajul conține `@NumePersonaj`,
răspunde doar personajul (sau personajele) menționat(e); dacă nu conține nicio mențiune, răspund
toate cele 5. Personajele văd ce a zis grupul până acum, nu doar ce am scris eu.

Regula de mențiuni e soluția minimă pentru această fază, nu decizia finală — o orchestrare mai
inteligentă (ex. personajele decid singure dacă au ceva de adăugat) rămâne de discutat într-o
etapă ulterioară a MVP-ului. **Depășit de M7.**

## M6 — Memorie și polish

Conversația supraviețuiește la refresh. Responsive pe telefon. **Parțial:** promisiunea „pot
scrie oricând, chiar peste un personaj care încă «scrie»" n-a fost implementată — caseta se
bloca până se termina runda. **Terminat abia la M9.**

## M7 — Cine răspunde: 80% chemații, 20% restul

Mențiunea devine o convocare sigură, nu doar un filtru: cine e chemat cu `@` răspunde
întotdeauna, iar nemenționații își împart 20% șansa de a interveni neinvitați — împărțită egal
la câți sunt, ca procentul să rămână valid când consiliul crește. Fără nicio mențiune, se
convoacă tot consiliul, ca la M5.

În plus, `@` scris de un personaj cheamă la fel ca `@` scris de mine: cel chemat răspunde în
aceeași rundă, la replica ce l-a chemat. Un singur val de lanț, nimeni de două ori pe rundă.

Aruncarea cu banul e injectată (`obligati_sa_raspunda(..., sansa=)` și `main.zaruri`), ca
testele să fie deterministe.

## M8 — Chat natural: memorie comună și dreptul de a tăcea

Personajele se aud între ele: `context_pentru` nu mai filtrează nimic, iar replicile altora
intră cu numele vorbitorului în față, ca să nu se topească toate vocile într-una. Fereastra
urcă de la 12 la 24 de mesaje — o rundă de consiliu întreg produce acum 6 mesaje, nu 2.

Contextul se citește la rândul fiecăruia, nu la începutul rundei, deci al doilea vorbitor aude
ce a zis primul. Fiecare răspunde ultimei replici din chat.

Nu mai răspund toți la orice: fiecare e întrebat și scrie `PAS` dacă n-are ce adăuga, iar
serverul îi înghite tăcerea. Cei chemați cu `@` și cei cărora le iese aruncarea de 20% nu au
voie să tacă — primesc `INDEMN_OBLIGAT` în plus la system prompt.

Costul, asumat: un mesaj cu o singură mențiune înseamnă acum un apel la model pentru fiecare
personaj, nu unul singur. Tăcerea nu se poate afla fără să întrebi.

## M9 — Am prioritate față de consiliu

Ce promitea M6 și nu făcea: caseta rămâne liberă cât vorbește consiliul, iar mesajul meu nou
taie runda în curs. Bula pe jumătate scrisă dispare de pe ecran și nu ajunge în istoric, cele
deja terminate rămân. Nu se suprapun două runde: fiecare rundă își știe numărul, iar cea veche
se oprește când numărul nu mai e al ei (`incepe_runda`, `runda_anulata` din `backend/main.py`).

Pe server, o rundă pe care n-o mai vede nimeni nu mai arde tokeni: pagina întrerupe fluxul cu
`AbortController`, iar generarea se oprește la prima bucată de după închiderea conexiunii
(`trebuie_oprita`). Așteptarea după model stă pe alt fir, ca bucla de evenimente să fie liberă
să primească mesajul care anulează runda — altfel „am prioritate" ar fi rămas o vorbă.

Curățat tot aici: fără nicio mențiune nu era nimeni obligat, deci toate cele 5 personaje puteau
scrie `PAS` și mesajul rămânea fără niciun răspuns pe ecran. Acum sorții scot exact un vorbitor
obligat — consiliul nu răspunde cu tăcere totală, dar nici nu se adună tot la orice mesaj, cum
făcea până la M8. Funcția `probabilitati` a dispărut: ramura ei „fără mențiune → toți 1.0" nu
era folosită de nimeni și spunea altceva decât se întâmpla.

## M10 — Tăcerea, ca s-o poată duce și un model de 2B

Regulile M7–M8 erau corecte în cod și invizibile în practică: pe `gemma4:e2b`, la o întrebare
tehnică adresată cu `@Programatorul`, răspundeau toate cele 5. PAS măsurat: **0 din 25**.
Testele treceau, pentru că verificau mecanica, nu modelul.

Trei schimbări în system prompt-uri (`personaje.json`, plus fișierele `personaj-*.md`):

1. **Regula de tăcere e ultima**, după toate celelalte, ca bloc separat — nu un punct la
   mijlocul listei, unde se pierde.
2. **Imperativă, nu permisivă**: „răspunsul tău este exact acest cuvânt: PAS. Nu explica, nu te
   scuza, nu saluta." în loc de „nu ești obligat să vorbești... scrie doar PAS".
3. **Criteriu concret în loc de judecată abstractă**: „Domeniul tău: <rol>." — un model de 2B nu
   poate cântări dacă „are o opinie fundamentată", dar poate compara subiectul cu o etichetă.

Măsurat pe 5 rulări × 5 personaje, înainte → după: pe subiect străin, întrebare de decizie
**0/25 → 25/25** tăceri; pe subiect străin, întrebare de cultură generală **0/25 → 10/25**
(modelul răspunde enciclopedic la ce știe, indiferent de rol — rămâne limita cunoscută); pe
domeniul propriu **0/25 → 0/25**, deci nimeni nu tace când nu trebuie. În runde adevărate,
întrebarea tehnică cu `@Programatorul` a trecut de la 5 vorbitori din 5 la 2–3.

`INDEMN_OBLIGAT` a rămas neschimbat: șase formulări măsurate, cea existentă e singura care ține
`@mențiunea` peste noua regulă (0/25 tăceri). Variantele care nu numesc „PAS" pierd catastrofal
(până la 19/25), iar cele care îl numesc de două ori îl fac mai proeminent, nu mai slab.

Ce n-a putut fi reparat din prompt: pe un mesaj fără conținut („Mulțumesc, notat."), 15 din 25
tac chiar și obligate. Sorții din M9 obligă un vorbitor, dar dacă tocmai el tace, runda iese
goală. Atunci serverul trimite `{"tip":"consiliul_tace"}` și pagina scrie o singură linie
discretă — tăcerea consiliului nu mai arată ca un server picat.

## Definiția de „gata"

1. Pornesc totul cu un singur pas (sau doi, dacă backend + frontend sunt separate) — nu o
   listă lungă de comenzi.
2. Scriu o întrebare din `concept-aplicatie-miyuki.md` §16 și primesc răspunsuri care se simt
   ca opinii, nu ca fișe de informații.
3. Cele 5 personaje sunt clar distincte — le recunosc fără să mă uit la nume.
4. Un personaj comentează ce a zis alt personaj, nu doar ce am zis eu.
5. Dau refresh și conversația e tot acolo.
6. Niciun `TODO` sau cod de test uitat în proiect.

## Ce rămâne explicit în afara acestei etape

Fără cont/login (dacă apare vreodată nevoia, e o decizie separată — vezi disputa rezolvată în
`personaj-programatorul.md`). Fără RAG, fără tool calling, fără căutare live în
`concept-aplicatie-miyuki.md` — cunoștințele personajelor sunt cele din system prompt-urile
lor, atât. Orchestrarea „deșteaptă" — personajele decizând singure dacă au ceva de adăugat —
a intrat la M8, dar în forma ei simplă: fiecare decide pentru el, prin `PAS`. Fără arbitru care
citește runda și împarte cuvântul, fără ca personajele să scrie nechemate, între mesajele mele.
