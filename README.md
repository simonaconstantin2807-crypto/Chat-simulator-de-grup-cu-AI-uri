# Consiliul CoSiMa

Chat de grup cu 5 personaje AI care dezbat decizii de produs pentru platforma CoSiMa.
Viziunea e în `SPEC.md`, etapele în `PLAN-IMPLEMENTARE.md`, convențiile de lucru în
`CLAUDE.md`, personajele în `personaje.json` (conținutul system prompt-urilor vine din
fișierele `personaj-*.md`).

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

- La fiecare mesaj sunt întrebate toate personajele, dar răspunde doar cine are ceva de spus.
  Cine n-are, scrie `PAS` — semnal care nu ajunge pe ecran și nu se salvează. Criteriul e
  domeniul fiecăruia, ultima instrucțiune din system prompt-ul lui (câmpul `rol` din
  `personaje.json`).
- Scrii `@Nume` (sau apeși pe personajul din bara de sus) → cine e chemat **nu are voie să
  tacă**. În timp ce scrii `@`, apare lista cu personaje: săgeți + Enter sau click.
- Nemenționații își împart 20% șansa de a fi obligați să contribuie chiar dacă n-aveau nimic de
  zis, ca discuția să nu se stingă (`PARTEA_NEMENTIONATILOR` din `backend/personaje.py`).
- Fără nicio mențiune nu e nimeni chemat, deci toți ar putea tăcea. Ca să nu rămâi cu ecranul
  gol, sorții obligă exact un vorbitor; restul decid fiecare pentru el. Dacă totuși n-a vorbit
  nimeni, pagina scrie „Consiliul n-a avut ce adăuga." — nu te lasă să te întrebi dacă s-a rupt
  ceva.
- Dacă un personaj scrie `@Nume` în replica lui, cel chemat răspunde imediat după și pierde și
  el dreptul de a tăcea. Nimeni nu vorbește de două ori în aceeași rundă.
- Conversația se salvează în `backend/data/conversatie.json` și e tot acolo după refresh sau
  după repornirea serverului.
- Poți scrie oricând, chiar peste un personaj care încă scrie: mesajul tău taie runda în curs.
  Replica pe jumătate scrisă dispare de pe ecran și nu se salvează, cele deja terminate rămân,
  iar pe server generarea se oprește — nu se ard tokeni pentru o rundă anulată.

## API

| Metodă | Rută             | Ce face                                                          |
| ------ | ---------------- | ---------------------------------------------------------------- |
| GET    | `/api/personaje` | Profilurile publice (nume, rol, avatar, culori) + utilizatoarea. |
| GET    | `/api/mesaje`    | Istoricul conversației.                                          |
| POST   | `/api/mesaje`    | Trimite un mesaj; răspunde cu flux NDJSON (vezi mai jos).        |
| GET    | `/api/health`    | Confirmă că modelul răspunde.                                    |

Fluxul de la `POST /api/mesaje` are câte un obiect JSON pe linie:
`{"tip":"personaj",...}` (cine începe să vorbească), `{"tip":"text","text":"..."}` (bucată de
răspuns), `{"tip":"gata"}` (mesaj terminat), `{"tip":"tace"}` (n-a avut ce adăuga — pagina
scoate bula de pe ecran), `{"tip":"consiliul_tace"}` (n-a vorbit nimeni în toată runda),
`{"tip":"eroare","text":"..."}`.

Fluxul se închide fără alt eveniment dacă runda a fost anulată — pentru că am trimis alt mesaj
peste ea sau pentru că pagina a închis conexiunea. Ce nu s-a terminat cu `{"tip":"gata"}` nu e
în istoric.

## Memoria personajelor

Fiecare personaj primește ultimele `MESAJE_IN_CONTEXT` mesaje (vezi `backend/istoric.py`) —
toată discuția, inclusiv replicile celorlalți, care vin cu numele vorbitorului în față.
Propriile replici rămân fără prefix, ca să nu învețe să-și semneze mesajele.

Contextul se citește la rândul fiecăruia, nu la începutul rundei: al doilea vorbitor aude ce a
zis primul și îi răspunde lui, nu neapărat mie.

## Ce rămâne pentru etapa următoare

- Conversație emergentă — grupul prinde viață, de la „eu moderez" la „ele vorbesc singure".
