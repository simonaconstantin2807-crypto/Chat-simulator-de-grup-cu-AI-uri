# Consiliul CoSiMa

Chat de grup cu 5 personaje AI care dezbat decizii de produs pentru platforma CoSiMa.
Viziunea e în `SPEC.md`, etapele în `PLAN-IMPLEMENTARE.md`, convențiile de lucru în
`CLAUDE.md`, scenariul de prezentare în `DEMO.md`, personajele în `personaje.json` (conținutul
system prompt-urilor vine din fișierele `personaj-*.md`).

## Ce îți trebuie

- [Ollama](https://ollama.com) pornit local, cu modelul din `backend/ai_client.py`
  (`MODEL_IMPLICIT`) descărcat.
- Python 3.12 și dependențele din `backend/requirements.txt`.

## Pornire

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Apoi deschide <http://127.0.0.1:8000>. Modelul se preîncarcă în fundal la pornire, ca primul
răspuns să nu aștepte cele câteva secunde de încărcare.

Dacă un personaj răspunde cu bula roșie „modelul nu a răspuns", motivul e scris în consola
serverului. Cel mai des e încărcarea la rece pe GPU, care pică din când în când pe mașina asta
(`0xc0000409` / „CUDA error"); e reîncercată automat o dată, după `PAUZA_REINCERCARE` secunde
(`backend/ai_client.py`), atât la preîncărcare cât și la prima cerere a unei runde. Dacă și a doua
oară pică, merită verificat `%LOCALAPPDATA%\Ollama\server.log`.

Se reîncearcă doar erorile de încărcare, recunoscute după urmele din `URME_INCARCARE_ESUATA`. Cu
Ollama oprit sau cu modelul nedescărcat, eroarea vine imediat — a doua încercare ar eșua la fel.

Teste:

```powershell
.venv\Scripts\python.exe -m pytest -m "not ollama"   # doar cele deterministe, ~1s
.venv\Scripts\python.exe -m pytest                   # tot, inclusiv modelul pe bune, ~30s
```

Testele care vorbesc cu Ollama pe bune sunt marcate `@pytest.mark.ollama` și cer serverul
Ollama pornit; restul merg oriunde. Cele din `tests/test_tacerea.py` verifică pe model că
regula de tăcere chiar funcționează — că un personaj scrie `PAS` la un subiect care nu e al
lui — singurul lucru pe care testele deterministe nu-l pot garanta.

## Cum se folosește

- La fiecare mesaj se aleg vorbitorii rundei, și numai ei sunt întrebați: `VORBITORI_PE_RUNDA`
  din `backend/personaje.py`, adică doi-trei când nu chemi pe nimeni. Nu tot consiliul — pe
  `gemma4:e2b`, la o întrebare largă criteriul de domeniu se potrivește pentru aproape toți,
  deci `PAS` n-are ce filtra și răspund patru-cinci, iar cei fără nimic de spus scot
  non-sequitur din inventarul lor.
- `PAS` rămâne pentru întrebarea îngustă: cine e ales fără să fie chemat pe nume poate tăcea, iar
  semnalul nu ajunge pe ecran și nu se salvează. Criteriul sunt subiectele fiecăruia, numite pe
  rând în ultima instrucțiune din system prompt-ul lui (rândul „Vorbești despre:" din
  `personaje.json`).
- Tot ca tăcere se tratează și replica prea scurtă ca să fie o contribuție — sub
  `LITERE_MINIME_REPLICA` litere (`backend/ai_client.py`), fără cifră și fără `@`. Apare când
  replica dinainte e o întrebare, iar modelul o ia literal și răspunde „Multe." Cine a fost
  chemat pe nume nu dispare din rundă: mai primește o încercare, la mesajul tău.
- Fiecare scrie cât îi stă în fire: Operatoarea și Clienta taie scurt, Maestra își face loc
  pentru un exemplu, Programatorul explică pe larg când decizia de azi ar forța o rescriere
  mâine. Regula de lungime e per personaj, cu cifra măsurată în `personaj-*.md`.
- Scrii `@Nume` (sau apeși pe personajul din bara de sus) → cine e chemat **nu are voie să
  tacă**. În timp ce scrii `@`, apare lista cu personaje: săgeți + Enter sau click.
- Peste cei chemați intră cel mult unul nechemat, cu șansa `PARTEA_NEMENTIONATILOR` din
  `backend/personaje.py` — o singură aruncare pentru toți, deci 20% rămâne 20% și când consiliul
  crește. Pe el l-au adus sorții, nu subiectul, așa că nici el n-are voie să tacă.
- Fără nicio mențiune nu e nimeni chemat, deci toți cei aleși ar putea tăcea. Ca să nu rămâi cu
  ecranul gol, sorții obligă exact un vorbitor dintre ei; restul decid fiecare pentru el. Dacă
  totuși n-a vorbit nimeni, pagina scrie „Consiliul n-a avut ce adăuga." — nu te lasă să te
  întrebi dacă s-a rupt ceva.
- Dacă un personaj scrie `@Nume` în replica lui, cel chemat răspunde imediat după și pierde și
  el dreptul de a tăcea, chiar dacă nu fusese ales la începutul rundei. Nimeni nu vorbește de
  două ori în aceeași rundă.
- Conversațiile stau în panoul din stânga: apeși pe una și o continui de unde ai rămas, faci
  una nouă din **+ Nouă**, o redenumești cu ✏️ (Enter salvează, Escape renunță) sau o ștergi cu
  🗑️. Pe telefon panoul e sertar și se deschide din butonul ☰ din header.
- Titlul se scrie singur din primele cuvinte ale primului tău mesaj; dacă îl schimbi tu, rămâne
  cum l-ai scris.
- Fiecare conversație are istoricul ei separat, într-un fișier al ei în
  `backend/data/conversatii/`. Personajele dintr-o conversație nu văd nimic din alta.
- Conversația deschisă e tot acolo după refresh sau după repornirea serverului. Discuția de
  dinainte de conversațiile multiple se mută singură la prima pornire, iar fișierul ei vechi
  rămâne pe disc ca `conversatie.json.migrat`.
- După ce se termină runda pornită de mesajul tău, conversația mai merge singură 2–4 replici, la
  câteva secunde una de alta, apoi se oprește și așteaptă. La fiecare vorbește un singur personaj:
  80% șanse să fie cineva chemat cu `@` și neajuns încă la cuvânt, 20% împărțit la ceilalți. Cine
  tocmai a vorbit nu începe și replica următoare, iar cel ales poate să tacă — atunci se încearcă
  altcineva. Câte replici, cât se așteaptă între ele și câte încercări are una: `REPLICI_AUTONOME`,
  `PAUZA_SECUNDE` și `INCERCARI_PE_REPLICA` din `backend/main.py`.
- Ce iese din fereastra de context nu se pierde: se strânge într-un rezumat scurt, pe care îl
  citești din rândul **Ce ține minte consiliul**, sub personaje. Apare abia după ce ședința
  depășește fereastra și se împrospătează la capătul unei runde.
- Cât timp ai text în caseta de input, nimeni nu vorbește de la sine. Se reia când trimiți sau
  când golești caseta.
- Poți scrie oricând, chiar peste un personaj care încă scrie: mesajul tău taie runda în curs.
  Replica pe jumătate scrisă dispare de pe ecran și nu se salvează, cele deja terminate rămân,
  iar pe server generarea se oprește — nu se ard tokeni pentru o rundă anulată.
- Mesajul tău e plafonat la `LITERE_IN_MESAJ` litere (`backend/main.py`), cât e și `maxlength`-ul
  casetei. Peste atât, modelul local scoate system prompt-ul din fereastră ca să facă loc
  textului și răspunde un asistent generic, fără personaj și fără regula de tăcere.

## API

| Metodă | Rută                            | Ce face                                                            |
| ------ | ------------------------------- | ------------------------------------------------------------------ |
| GET    | `/api/personaje`                | Profilurile publice (nume, rol, avatar, culori) + utilizatoarea.   |
| GET    | `/api/conversatii`              | Lista conversațiilor, cea folosită ultima prima. Fără mesaje.      |
| POST   | `/api/conversatii`              | Conversație nouă, goală și fără titlu.                             |
| PATCH  | `/api/conversatii/{id}`         | Redenumește; corpul e `{"titlu": "..."}`.                          |
| DELETE | `/api/conversatii/{id}`         | Șterge; răspunde cu lista rămasă (mereu măcar una).                |
| GET    | `/api/conversatii/{id}/mesaje`  | Istoricul conversației.                                            |
| GET    | `/api/conversatii/{id}/rezumat` | Memoria lungă: `{"rezumat": "...", "panaLa": n}`.                  |
| POST   | `/api/conversatii/{id}/mesaje`  | Trimite un mesaj; răspunde cu flux NDJSON (vezi mai jos).          |
| POST   | `/api/conversatii/{id}/continuare` | O replică pe care consiliul și-o dă singur; corpul e `{"runda": n}`. |
| GET    | `/api/health`                   | Spune dacă modelul răspunde. Cu Ollama oprit, `model_raspunde: false`, nu eroare de server. |

Un `id` care nu există dă 404, iar un mesaj peste plafon dă 422 — în ambele cazuri pagina scrie
în bulă că serverul a refuzat cererea, în loc să lase punctele să se învârtă. Conversația e
listată cu `id`, `titlu` (gol dacă n-a fost încă scris niciun mesaj în ea), `creatLa`,
`actualizatLa` și `numarMesaje`.

Fluxul de la `POST /api/conversatii/{id}/mesaje` are câte un obiect JSON pe linie:
`{"tip":"personaj",...}` (cine începe să vorbească), `{"tip":"text","text":"..."}` (bucată de
răspuns), `{"tip":"gata"}` (mesaj terminat), `{"tip":"tace"}` (n-a avut ce adăuga — pagina
scoate bula de pe ecran), `{"tip":"consiliul_tace"}` (n-a vorbit nimeni în toată runda),
`{"tip":"eroare","text":"..."}` și, la sfârșitul unei runde în care a vorbit cineva,
`{"tip":"rezumat","text":"..."}` (doar când memoria lungă chiar s-a schimbat) urmat de
`{"tip":"continua","runda":n,"replici":3,"pauzaSecunde":[5,20]}` — câte replici mai duce
conversația singură, cât să aștepte pagina între ele și din ce rundă vin.

Fluxul de la `POST /api/conversatii/{id}/continuare` are aceleași evenimente, pentru o singură
replică (mai puțin `continua` și `consiliul_tace`). Pagina îl cere după pauză, cu numărul de
rundă primit; dacă între timp am trimis alt mesaj, replica e refuzată și fluxul vine gol.

Fluxul se închide fără alt eveniment dacă runda a fost anulată — pentru că am trimis alt mesaj
peste ea sau pentru că pagina a închis conexiunea. Ce nu s-a terminat cu `{"tip":"gata"}` nu e
în istoric.

## Memoria personajelor

Fiecare personaj primește ultimele `MESAJE_IN_CONTEXT` mesaje din conversația curentă (vezi
`backend/istoric.py`) — toată discuția de acolo și numai de acolo, inclusiv replicile celorlalți,
care vin cu numele vorbitorului în față.
Propriile replici rămân fără prefix, ca să nu învețe să-și semneze mesajele.

Contextul se citește la rândul fiecăruia, nu la începutul rundei: al doilea vorbitor aude ce a
zis primul și îi răspunde lui, nu neapărat mie.

### Memoria lungă

Ce iese din fereastră se comprimă într-un rezumat de cel mult `RANDURI_REZUMAT` rânduri
(`backend/rezumat.py`): `Subiect:`, `Decizii:` și câte o poziție de personaj. Se rescrie când s-au
strâns `MESAJE_PE_REZUMAT` replici nerezumate, la capătul unei runde, și se rescrie *incremental*
— modelul primește rezumatul de până atunci plus doar lotul nou, nu toată ședința.

Rezumatul se lipește la coada system prompt-ului, prin `bloc_pentru_prompt`, nu în lista de
mesaje. Nu e o preferință: `gemma4:e2b` n-are rol `system` nativ, iar un bloc pus în fața
contextului îngroapă `INDEMN_OBLIGAT` la mijlocul primului mesaj și strică regula de la M10 —
cifrele sunt în docstring și în `PLAN-IMPLEMENTARE.md`. Cele două teste `ollama` din
`tests/test_tacerea.py` păzesc exact asta.

Rezumatul stă în fișierul conversației, lângă mesaje, deci ține la restart și rămâne al ei. Dacă
modelul nu răspunde, ce se ținea minte rămâne neatins și lotul se reia la runda următoare.

## Ce rămâne pentru etapa următoare

- Nimic în lucru. Ce e explicit în afara scopului (cont, RAG, tool calling, arbitru care împarte
  cuvântul) e listat în `PLAN-IMPLEMENTARE.md`.
