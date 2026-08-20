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

**Depășit de M15** la partea de „cine e întrebat": nemenționații nu mai primesc fiecare câte o
aruncare, ci intră cel mult unul, tras la sorți dintr-o singură aruncare. Convocarea prin `@` și
lanțul de mențiuni rămân exact cum sunt descrise aici.

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

**Depășit de M15**, și tocmai pe costul ăsta: nu se mai întreabă toți, se aleg vorbitorii. `PAS`
rămâne, dar ca plasă de siguranță pentru întrebarea îngustă — motivul e măsurat, e acolo.

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

## M11 — Conversații multiple

Până acum exista o singură discuție, în `backend/data/conversatie.json`. Acum sunt mai multe,
separate: aleg una din listă și o continui din punctul unde am rămas, fac una nouă dintr-un
buton, o redenumesc sau o șterg.

Fiecare conversație e un fișier al ei, în `backend/data/conversatii/`, cu titlul și mesajele
înăuntru. Rămâne JSON din același motiv ca la M6: deschid fișierul și văd ce a primit modelul.
Lista se obține citind folderul, fără fișier-index — un index ar fi fost mai rapid, dar ar fi
însemnat două surse de adevăr care se pot desincroniza.

Titlul se scrie singur din primele cuvinte ale primului meu mesaj (`titlu_din_mesaj` din
`backend/istoric.py`). Titlul gol înseamnă „încă nenumită", deci nu e nevoie de niciun câmp în
plus ca să se știe dacă se mai poate genera: un titlu pus de mine e o decizie și nu mai e
înlocuit de nimic.

Izolarea e în `context_pentru`, care primește acum și conversația: personajele dintr-una nu văd
nimic din alta, nici măcar în context. `MESAJE_IN_CONTEXT` rămâne neschimbat — fiecare
conversație are istoricul ei, deci și fereastra ei.

Conversația deschisă se ține în `localStorage`, nu pe server: nu există cont, iar serverul n-are
de unde ști în care dintre ele mă uit. Dacă între timp a fost ștearsă, pagina cade pe cea mai
recentă. Serverul lasă mereu măcar o conversație în urmă, ca ștergerea ultimei să nu mă lase
fără niciun loc în care să scriu.

Conversația de dinainte se migrează singură la prima pornire care o găsește: devine prima din
listă, cu titlul luat din primul meu mesaj. Fișierul vechi e redenumit în `conversatie.json.migrat`,
nu șters — lipsa lui e și semnalul că migrarea s-a făcut deja, deci nu se repetă la restart.

În interfață, lista stă într-un panou lateral fixat la stânga peste 900px, iar sub 900px devine
sertar peste conversație, deschis din butonul `☰` din header. Coloana de chat rămâne exact cum
era, cu aceleași lățimi, deci și pe 390px arată ca înainte. Alternativa — o bară de conversații
deasupra — ar fi mâncat din înălțime tocmai pe ecranul unde e cea mai scumpă.

## M12 — Conversația continuă singură, cu limită

Partea din sesiunea 11 care lipsea: „de la eu moderez la ele vorbesc singure", dar limitat. După
runda pornită de mesajul meu, conversația mai merge de la sine 2–4 replici (`REPLICI_AUTONOME`
din `backend/main.py`), apoi se oprește și așteaptă. Plafonul e ales pe măsurătoare, nu din
prudență: pe `gemma4:e2b`, după vreo 8–10 replici autonome discuția intră în buclă și personajele
se repetă — se oprește înainte, nu după.

La fiecare replică autonomă vorbește **unul singur**, ales probabilistic — aici se aplică regula
80/20 în forma din slide-uri, spre deosebire de mecanica de la M7–M8, unde e întrebat fiecare și
răspunde cine are ceva de zis. `PARTEA_CHEMATILOR` (`backend/personaje.py`) merge către cei
chemați cu `@` și neajunși încă la cuvânt (`chemati_fara_raspuns`), restul se împarte la ceilalți
(`alege_vorbitorul`). Cine tocmai a vorbit e exclus din alegerea imediat următoare — două replici
la rând de la același personaj n-ar mai fi o conversație de grup.

Cel ales poate tot să scrie `PAS`, fără `INDEMN_OBLIGAT`: nu l-a chemat nimeni pe nume. Dacă
tace, replica nu se consumă degeaba — se încearcă altcineva, dar în limita `INCERCARI_PE_REPLICA`,
altfel o discuție stinsă ar cere un apel la model pentru fiecare personaj, la fiecare replică.

**Transport: tot streaming NDJSON, nu polling.** Slide-urile sesiunii 11 sugerează polling, dar
ar fi însemnat să arunc `AbortController`-ul și oprirea generării de la M9 și să înlocuiesc un
canal care merge cu unul care întreabă în gol. Runda pornită de mesajul meu se termină acum cu un
eveniment `{"tip":"continua"}`, care spune paginii câte replici mai urmează, cât să aștepte între
ele și din ce rundă vin. Pagina le cere una câte una, la `POST /api/conversatii/{id}/continuare`,
fiecare cu fluxul ei — aceleași evenimente ca la o rundă obișnuită.

Împărțirea asta pică natural: **pauza o ține pagina, alegerea vorbitorului o ține serverul.** Doar
pagina știe dacă am început să scriu — regula 3 din sesiunea 11, „cât am text în caseta de input,
nimeni nu vorbește" — și doar ea știe în ce conversație mă uit. Serverul rămâne fără stare între
replici, ca până acum. Numărul rundei călătorește dus-întors (`ContinuareIntrare`): o replică
rămasă dintr-o rundă peste care am scris e refuzată pe server, nu doar anulată în pagină.

Intervalul de pauză stă într-un singur loc, `PAUZA_SECUNDE` din `backend/main.py`, și ajunge în
pagină prin evenimentul `continua`. Slide-urile sugerează 0–300s; cinci minute între replici sunt
absurde pentru o ședință de 20 de minute, deci 5–20s.

Aruncările sunt injectate ca peste tot: `main.zaruri` pentru numărul de replici și pentru alegerea
vorbitorului, `alege_vorbitorul(..., sansa=)` în teste.

## M13 — Memorie lungă prin rezumat rulant

`MESAJE_IN_CONTEXT` e 24. La mesajul 40, primele 16 dispăruseră complet: nimeni nu mai avea de
unde ști ce s-a decis la începutul ședinței, iar scopul din `SPEC.md` — „ies din conversație cu o
decizie" — nu se ținea nicăieri *ca decizie*. Măsurat pe `gemma4:e2b`, cu decizia împinsă în afara
ferestrei: la întrebarea „unde am decis să generăm preview-ul?", Programatorul a răspuns pe dos,
**4 din 4** rulări. Cu rezumatul, **4 din 4** corect.

Ce iese din fereastră intră într-un rezumat de cel mult `RANDURI_REZUMAT` rânduri
(`backend/rezumat.py`): `Subiect:`, `Decizii:` și câte o poziție de personaj. Se actualizează
incremental — secretarul primește rezumatul de până atunci plus doar lotul tocmai ieșit, nu
ședința de la capăt — și se reface la capătul rundei, pe alt fir, unde cele 2–4 secunde nu se
simt. Un lot e `MESAJE_PE_REZUMAT`, adică o rundă de consiliu întreg: un apel în plus la fiecare
mesaj s-ar fi văzut. Rezumatul stă în fișierul conversației, deci ține la restart, și e al ei.

**Modelul mic nu ține formatul, deci nu i se cere să-l țină.** Pe o ședință reală de 101 mesaje,
răspunsul brut avea între 5 și 14 rânduri și repeta același personaj de două-trei ori, cu poziții
diferite. Structura se impune determinist, în `scurteaza`: ultima poziție per nume, `Subiect` și
`Decizii` în față, tăiat la `RANDURI_REZUMAT`. Două formulări din șablon sunt și ele măsurate:
fără „cel mult trei", rândul `Decizii` ajungea la vreo nouăzeci de cuvinte și mânca bugetul de
tokeni; fără „adunat", modelul îngheța prima decizie și nu mai adăuga niciodată alta.

**Unde stă blocul a fost decis de măsurătoare, nu de estetică.** `gemma4:e2b` n-are rol `system`
nativ: Ollama lipește system prompt-ul de primul mesaj `user`. Un bloc pus în fața contextului
îngroapă la mijlocul acelui mesaj tocmai ce trebuie să fie ultimul — regula de tăcere și
`INDEMN_OBLIGAT` de la M10. Clienta, chemată pe nume pe un subiect străin, a tăcut la 15 rulări:
0/15 fără memorie, **14/15 cu blocul primul în context**, 9/15 cu el ultimul în context, 1–3/15
lipit la coada system prompt-ului, cum e acum. Celelalte două reguli rămân neatinse: pe subiect
străin, nechemată, tot 15/15 tăceri; pe domeniul ei, tot 0/15. Și antetul contează: varianta
explicită „Nu e o replică din chat…" duce înapoi la 13/15, pentru că ultima propoziție dinaintea
indemnului trage spre tăcere dacă e negativă. Antetul rămâne scurt și afirmativ. Cele două teste
din `backend/tests/test_tacerea.py` marcate `ollama` sunt garda care prinde regresia — testele
deterministe n-o pot vedea.

O eroare de model nu strică ce se ținea deja minte: lotul rămâne nerezumat și se reia la runda
următoare. Un consiliu care își uită deciziile pentru că Ollama a clipit ar fi mai rău decât unul
fără memorie lungă.

În interfață, rezumatul e un rând pliabil sub personaje, „Ce ține minte consiliul". Se încarcă la
deschiderea conversației și se împrospătează singur din evenimentul `{"tip":"rezumat"}`, la
capătul rundei.

**Limita rămasă, pe modelul ăsta:** rândul care îmi atribuie mie o poziție e uneori doar ultima
mea întrebare, iar la buget de tokeni epuizat ultimul rând poate ieși tăiat la mijloc de cuvânt
(o dată la opt rescrieri, la 300 de tokeni; de-asta `MAX_TOKENI_REZUMAT` e 360). Se repară singur
la rescrierea următoare. Subiectul și deciziile — partea pentru care există rezumatul — ies
corect.

## M14 — Polish și pregătire pentru prezentare

Ultima etapă. Nimic nou ca funcționalitate: voci mai distincte, regula de tăcere verificată pe
model, marginile care se rup, și un scenariu de demo repetat cu cronometrul.

**Vocile.** Toate cele cinci aveau aceeași regulă de lungime — „1-3 propoziții scurte". Într-un
grup real unul scrie trei cuvinte și altul un paragraf, așa că regula a devenit una per personaj,
scrisă pozitiv (ce face personajul, nu ce să nu facă). Măsurat pe `gemma4:e2b`, mediana replicii
de pe domeniul propriu: Operatoarea **5** cuvinte, Clienta **6**, Antreprenoarea **32**,
Programatorul **39**, Maestra **51**. Fiecare fișier `personaj-*.md` are acum un „Nivel de
energie" cu cifra lui.

**Regula de tăcere, verificată pe bune.** M10 o măsurase pe o singură întrebare străină și
raportase 25/25. La M14 s-a măsurat pe **10 întrebări strict tehnice diferite**, și acolo se
vedea altceva: Clienta tăcea **2 din 10**, Operatoarea 1, Antreprenoarea 2, Maestra 4. Eticheta
scurtă de la M10 („Domeniul tău: <rol>.") e prea vagă când întrebarea nu seamănă cu întrebarea
de test.

Înlocuită cu subiectele numite concret („Vorbești despre: cum arată bijuteria, cât de repede și
de simplu se comandă…"). După, pe 20 de întrebări: Clienta **7/20**, Operatoarea 9/20,
Antreprenoarea 10/20, Maestra 15/20, Programatorul 2/20 — și el corect, subiectul chiar e al lui.
Pe domeniul propriu nimeni n-a tăcut mai mult de 2 din 12, deci regula n-a devenit mutism.

Din listă a ieșit „coduri DB" la Operatoarea: cuvântul „cod" o chema la orice întrebare de
programare (1/10 tăceri cu el, 8/10 fără). La Antreprenoarea a intrat „nume și domeniu", fără
care tăcea tocmai la întrebarea din §16.4, care e a ei.

**Ce n-a mers, și de ce contează.** Odată cu vocile, blocul de reguli fusese trecut tot în limbaj
pozitiv, inclusiv cele două reguli care începeau cu „NU". Rezultat măsurat, pe Clienta, 15 rulări:
chemată pe nume pe subiect străin, cu memorie lungă în prompt, tăcea **10 din 15** — adică
`@mențiunea` nu mai era o convocare. Și pe domeniul ei, nechemată, tăcea **14 din 15**. Izolarea
pe jumătăți de prompt (corp × coadă, 4 combinații) a arătat că vinovat e corpul, nu criteriul de
domeniu; cele două reguli au fost puse la loc în forma lor măsurată. După revenire, toate cele
cinci garanții sunt identice cu M13: chemată 0/15, chemată cu memorie 0/15, domeniul ei 0/15,
domeniul ei cu memorie 0/15, subiect străin nechemată 15/15.

Limita rămasă: 3,5 din 10 la Clienta, nu mai mult. Două formulări mai apăsate (verificare
explicită înainte de a scrie, exemple de subiecte străine) n-au adus nimic peste zgomot — 7/20 și
8/20 față de 7/20.

**Marginile.** Cinci lucruri care se rupeau, fiecare cu testul lui:

1. **`PAS` ajungea pe ecran.** Modelul scrie uneori „PAS." și continuă cu replica adevărată —
   4 din 12 replici la măsurătoare. `fara_pas` tăia doar abținerea curată. Acum taie și semnalul
   din față, cerând punctuație după el, ca „Pas cu pas" să rămână întreg.
2. **Mesajul foarte lung.** Peste ~20.000 de litere Ollama scoate system prompt-ul din fereastră
   ca să facă loc mesajului: răspunde un asistent generic, fără personaj și fără regula de tăcere
   (măsurat la 20.000 și la 100.000). Plafon la `LITERE_IN_MESAJ`, în `main.py` și ca `maxlength`
   în pagină, deci refuzul nu se vede niciodată din interfață.
3. **`/api/health` cu Ollama oprit** răspundea cu eroare de server, deci nu se putea distinge un
   server picat de un model picat. Acum răspunde `model_raspunde: false`.
4. **Conversația ștearsă în timpul unei runde** era recreată de replica rămasă. `salveaza_mesaj`
   spune acum dacă a avut unde scrie, iar replica fără casă nu se mai anunță ca terminată.
5. **Lista de conversații se aranja aleator.** `_acum()` se baza pe microsecundele lui
   `datetime.now()`, dar ceasul Windows stă pe loc ~15ms: șase apeluri la rând dau aceeași
   valoare, iar la egalitate sortarea cădea pe sufixul aleator din id — conversația tocmai făcută
   putea ajunge sub una veche. `_acum()` e acum strict crescător. Ăsta explică și testul care
   pica din când în când la suita întreagă.

Un răspuns care nu e flux (404, 422, 500) e tratat explicit în pagină: până acum punctele de
„scrie…" se învârteau până la mesajul următor.

**Demo-ul** e în `DEMO.md`: întrebarea (§16.7, unde Maestra și Clienta au interese opuse), ce se
arată în ce ordine, ce fac dacă modelul răspunde prost live, și cronometrul real. Repetat de la
cap la coadă în Chrome, pe pagina adevărată: **74 de secunde** de mașină din cele 5-7 minute.

## M15 — Cine ia cuvântul se hotărăște înainte, nu prin `PAS`

De la M8, runda pornită de mesajul meu întreba toate cele cinci personaje și lăsa `PAS` să
filtreze. M10 și M14 au făcut filtrul să funcționeze — dar numai pentru întrebarea **îngustă**.

La una largă n-are ce filtra. La „vreau să dezvolt o aplicație de generare tipare pentru
bijuterii Miyuki", subiectul le pică aproape tuturor în domeniu, deci criteriul se potrivește
*corect* și pentru cine n-are nimic de spus. Ce iese e non-sequitur din inventarul propriu —
măsurat, pe exact acel mesaj:

```
Antreprenoarea : MVP-ul trebuie să fie un generator de tipare bazat pe dimensiuni... abonament lunar.
Clienta        : Super, vreau să văd cum arată în roz.
Maestra        : PAS
Operatoarea    : PAS
Programatorul  : Sunt gata să începem. Trebuie să decidem cum vom structura lucrurile...
```

Replica Clientei e chiar cazul: criteriul ei („cum arată bijuteria") s-a potrivit, dar la o
întrebare de fezabilitate n-avea ce căuta.

**Reparat prin selecție, nu prin prompt.** Prompturile merg 5/5 pe întrebări înguste (M14), deci
n-aveau ce repara. Se alege dinainte cine ia cuvântul, cu `alege_vorbitorul`, funcția care exista
deja și era testată de la M12:

- Cei chemați cu `@` intră toți, garantat. Neschimbat.
- Fără nicio mențiune se aleg `VORBITORI_PE_RUNDA` — doi-trei, tras la sorți — nu toți cinci.
- Peste cei chemați intră cel mult **unul** nechemat, cu `PARTEA_NEMENTIONATILOR`. Aruncarea e
  una singură pentru toți, în loc de una de fiecare cu pragul împărțit la câți sunt: iese același
  20%, dar fără împărțire, deci procentul rămâne valid oricât ar crește consiliul. Plafonul de
  unul singur contează — fără el runda ar crește la loc la patru-cinci guri.
- `PAS` rămâne. Cine e ales fără să fie chemat pe nume poate tot să tacă, iar acolo `PAS` e plasa
  de siguranță pentru întrebarea îngustă, pe care selecția n-are cum s-o judece. Cel intrat pe
  cei 20% e obligat: pe el l-au adus sorții, nu subiectul.
- Fără mențiune, sorții obligă un vorbitor **dintre cei aleși** (M9 rămâne). Unul neales n-ar fi
  întrebat oricum, deci obligația lui n-ar fi ajuns nicăieri.
- Nimeni nu vorbește de două ori. Lanțul de `@mențiuni` între personaje e neatins: cel chemat de
  altcineva trece în fața cozii și pierde dreptul de a tăcea, chiar dacă nu fusese ales la
  început.

`ordinea_vorbitorilor` a dispărut — întorcea tot consiliul și n-o mai chema nimeni. La fel ca
`probabilitati` la M9: cod care descria altceva decât se întâmplă.

**Măsurat pe `gemma4:e2b`, câte 5 runde de fiecare fel:**

| Mesaj | Înainte: vorbesc / apeluri / timp | După: vorbesc / apeluri / timp |
| --- | --- | --- |
| Larg („vreau să dezvolt o aplicație…") | 2,4 / 5 / 5,0s | 1,4 / 2,8 / **3,0s** |
| Îngust („cât durează o comandă specială?") | 4,0 / 5 / 5,5s | 2,0 / 2,2 / **2,5s** |
| Cu `@Maestra` | 1,2 / 5 / 5,0s | 1,0 / 1,0 / **2,0s** |

Runda se termină în aproape jumătate din timp, pentru că nu mai costă cinci apeluri la model.

**Ce s-a văzut la măsurătoare și nu se aștepta:** după listele de subiecte de la M14, întrebarea
largă aducea deja doar 2,4 vorbitori din 5, nu 4-5. Iar cea mai aglomerată rundă nu era cea largă,
ci una **îngustă** despre timpi de execuție (4,0 din 5) — acolo criteriul chiar se potrivește
pentru patru dintre ei. Selecția o scurtează și pe aceea.

**Compromisul, spus pe față:** pe întrebarea largă vorbesc acum 1,4 în medie, mai puțin decât cele
2,4 dinainte, pentru că dintre cei doi-trei aleși doar unul e obligat și ceilalți pot tăcea. Dacă
o rundă de un singur vorbitor e prea săracă, obligarea tuturor celor aleși e o linie în
`obligati_sa_raspunda` — dar atunci `PAS` nu mai are unde să se declanșeze în runda pornită de
mine, deci întrebarea îngustă ar aduce înapoi replici de umplutură.

## M16 — Replica degenerată se tratează ca tăcere

„Fiecare răspunde ultimei replici din chat" (M8) are un efect secundar care se vede doar pe un
model mic: **când replica dinainte e o întrebare, ea ajunge ca întrebare adresată lui**
(`intrebare = context.pop()` în `replica_personajului`), iar modelul o ia literal. Operatoarea a
întrebat „Cât de multe coduri Miyuki sunt necesare pentru o formă dată?", iar Clienta a răspuns
„Multe."

Regula nu se schimbă — tot ea produce și replicile bune, cele care decurg din ce a zis altcineva,
adică punctul 4 din definiția de „gata". Se taie rezultatul, nu regula.

**Pragul.** `LITERE_MINIME_REPLICA` (`backend/ai_client.py`), lângă `SEMNAL_PAS`, pentru că e
aceeași cale: sub 15 litere, fără cifră și fără `@`, replica se tratează ca tăcere — nu ajunge pe
ecran, nu intră în istoric. Cele două excepții există ca pragul să nu mănânce tocmai vocile care
vorbesc scurt din fire: „~30g" e chiar contribuția Operatoarei, iar „@Maestra?" pornește replica
altcuiva. Filtrarea e în **stream** (`fara_replici_degenerate`), din același motiv ca la `PAS`:
altfel „Multe." ar apărea și ar dispărea sub ochii utilizatoarei.

**Cel obligat nu are voie să dispară.** Dacă l-am chemat pe nume și tot scoate o replică
degenerată, înghițirea ei l-ar șterge cu totul din rundă — adică exact runda goală pe care a
reparat-o M9, dar de data asta după ce am convocat pe cineva explicit. Soluția aleasă:
**a doua încercare, la mesajul meu.** Nu e o repetare a aceluiași apel — atacă tocmai cauza:
întrebarea care l-a încurcat iese din context (`_context_dinaintea_mesajului_meu`), iar el
răspunde mesajului meu, cel care l-a și convocat. După a doua încercare nu se mai insistă:
tăcerea se anunță ca atare, prin `consiliul_tace`.

Măsurat pe `gemma4:e2b`, Clienta obligată, cu întrebarea Operatoarei ca ultimă replică:

| | |
| --- | --- |
| Prima încercare, la întrebarea Operatoarei | **6/6 degenerate** — „Nu știu." de fiecare dată |
| A doua încercare, la mesajul meu | **6/6 replici bune** — „Serios? Nu vreau nicio aplicație, vreau doar să văd cum arată în roz." |

Alternativele respinse: să lase replica degenerată pe ecran când vine de la cel convocat (arată
exact problema pe care o repar), și să repete același apel (la temperatura 0,3 a Operatoarei,
al doilea răspuns e adesea primul).

**Costul, asumat:** cel obligat care tace consumă acum două apeluri la model, nu unul. Se
întâmplă și în cazul cunoscut de la M10 — pe un mesaj fără conținut („Mulțumesc, notat."),
obligatul tace uneori — unde a doua încercare e la fel de binevenită. Ceilalți aleși n-au a doua
șansă: nu li s-a cerut nimănui să vorbească.

## M17 — Încărcarea la rece care pică, și eroarea care nu se vedea nicăieri

Un mesaj trimis după o pauză mai lungă s-a ales cu bula roșie „modelul nu a răspuns". Nu se
putea afla de ce: `replica_personajului` prindea excepția și o arunca, fără s-o scrie nicăieri.

Cauza, găsită în `%LOCALAPPDATA%\Ollama\server.log`:

```
14:15:57 ERROR llama-server terminated  exit status 0xc0000409
         CUDA error: shared object initialization failed
```

E **exact** eroarea pentru care exista workaround-ul `num_gpu: 0`, despre care comentariul din
`ai_client.py` scria că e rezolvată în Ollama 0.32.14. Nu e rezolvată — e doar rară: în aceeași
zi, din patru încărcări la rece, trei au mers și una a picat, iar încercarea următoare a mers.
Comentariul e actualizat cu măsurătoarea nouă, nu dublat cu una la coadă.

Două schimbări, amândouă mici:

1. **`_bucati_cu_reincercare`** (`backend/ai_client.py`): dacă modelul crapă **înainte de primul
   cuvânt**, se mai încearcă o dată. Condiția contează — dacă ar cădea după ce a scris ceva, a
   doua încercare ar dubla textul în bulă, iar utilizatoarea a și citit prima jumătate. Costul,
   când Ollama chiar e oprit: două conexiuni refuzate în loc de una, adică milisecunde.
2. **Motivul ajunge în log.** Pe ecran rămâne bula roșie scurtă, dar în consola serverului se
   scrie excepția, ca și la `incalzeste_modelul` și `actualizeaza_rezumat`. Fără ea nu se poate
   distinge Ollama oprit de o încărcare picată pe GPU sau de un model nedescărcat.

Ce **nu** s-a schimbat: nu se reintroduce `num_gpu: 0`. Când modelul chiar se încarcă, merge pe
GPU cu cifrele de la M0 — 1,59 GB VRAM, 84,5 tokeni/s. Workaround-ul ar aduce înapoi cele ~98s de
încărcare pe CPU și crash-urile în rafală.

## Definiția de „gata"

1. Pornesc totul cu un singur pas (sau doi, dacă backend + frontend sunt separate) — nu o
   listă lungă de comenzi.
2. Scriu o întrebare din `concept-aplicatie-miyuki.md` §16 și primesc răspunsuri care se simt
   ca opinii, nu ca fișe de informații.
3. Cele 5 personaje sunt clar distincte — le recunosc fără să mă uit la nume.
4. Un personaj comentează ce a zis alt personaj, nu doar ce am zis eu.
5. Dau refresh și conversația e tot acolo — chiar cea în care eram, dintre mai multe.
6. Niciun `TODO` sau cod de test uitat în proiect.

### Verificat la M14, punct cu punct

Toate șase trec. Verificarea s-a făcut pe 20 august 2026, pe `gemma4:e2b`, cu serverul pornit
exact cu comanda din `README.md`, iar pașii de interfață au fost jucați automat în Chrome, pe
pagina adevărată — nu bifați din ochi.

1. **Un singur pas.** `cd backend` + `.venv\Scripts\python.exe -m uvicorn main:app --reload`, apoi
   `GET /` răspunde 200 și `GET /api/health` răspunde `model_raspunde: true`. Fără al doilea pas:
   frontendul e servit de același proces.
2. **Întrebare din §16, răspunsuri care se simt ca opinii.** §16.7 (arătăm AB-ul în preview deși
   simularea nu e fidelă?): Maestra — „AB-ul nu se poate simula fidel pe ecran, așa că nu merită
   să ne deranjăm cu el"; Clienta — „Vreau să văd doar culorile." Poziții, nu fișe.
3. **Cele 5 sunt clar distincte.** De la M14 și măsurabil, nu doar la citire: mediana replicii e
   5 cuvinte la Operatoarea, 6 la Clienta, 32 la Antreprenoarea, 39 la Programatorul, 51 la
   Maestra. Se recunosc după lungime înainte de a ajunge la conținut.
4. **Un personaj comentează ce a zis altul.** În runda de la punctul 2, Programatorul a propus
   compromisul dintre poziția Maestrei și cea a Clientei — nu mi-a răspuns mie.
5. **Refresh și conversația e tot acolo, chiar cea în care eram.** După reload, subtitlul era tot
   `@Maestra merita sa simulam…` și cele 106 mesaje ale ei, deși nu era prima din listă.
6. **Fără `TODO`/`FIXME`/`XXX`, cod comentat sau harness uitat.** Căutare peste tot ce nu e în
   `arhiva/`: zero, în afară de textul regulii din `CLAUDE.md` și din lista de mai sus. Cele două
   `print` rămase în `backend/` sunt avertismentele din `incalzeste_modelul` și
   `actualizeaza_rezumat`, ambele pe căi de eroare documentate, nu depanare uitată. Măsurătorile
   de la M14 s-au făcut în scratchpad, în afara proiectului.

Suita: **216 de teste, ~28s** (la M17), inclusiv cele cinci care vorbesc cu modelul pe bune.

## Ce rămâne explicit în afara acestei etape

Fără cont/login (dacă apare vreodată nevoia, e o decizie separată — vezi disputa rezolvată în
`personaj-programatorul.md`). Fără RAG, fără tool calling, fără căutare live în
`concept-aplicatie-miyuki.md` — cunoștințele personajelor sunt cele din system prompt-urile
lor, atât. Orchestrarea „deșteaptă" — personajele decizând singure dacă au ceva de adăugat —
a intrat la M8, dar în forma ei simplă: fiecare decide pentru el, prin `PAS`. Fără arbitru care
citește runda și împarte cuvântul. Personajele scriu și între mesajele mele, dar numai de la M12
încoace și numai în limita de acolo: 2–4 replici după runda mea, apoi tăcere până scriu eu din
nou. Conversațiile multiple (M11) n-au adus nici cont, nici bază de date: tot local, tot în JSON.
Memoria lungă (M13) nu e RAG: nu caută nimic, nu indexează nimic — comprimă doar ce a ieșit din
fereastra propriei conversații.
