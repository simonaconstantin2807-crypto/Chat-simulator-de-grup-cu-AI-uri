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
etapă ulterioară a MVP-ului.

## M6 — Memorie și polish

Conversația supraviețuiește la refresh. Pot scrie oricând, chiar peste un personaj care încă
„scrie" — runda în curs se anulează curat, nu se suprapun răspunsuri. Responsive pe telefon.

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
lor, atât. Fără orchestrare „deșteaptă" (personajele decizând singure cine răspunde) — la M5
rămânem la regula simplă de mențiuni `@NumePersonaj`, urmează să fie rediscutată într-o etapă
viitoare.
