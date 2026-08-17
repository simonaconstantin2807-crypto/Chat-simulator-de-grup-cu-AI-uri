# Consiliul CoSiMa

Chat de grup cu 5 personaje AI care dezbat decizii de produs pentru platforma CoSiMa.
Viziunea e în `SPEC.md`, etapele în `PLAN-IMPLEMENTARE.md`, personajele în `personaje.json`
(conținutul system prompt-urilor vine din fișierele `personaj-*.md`).

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

Teste: `.venv\Scripts\python.exe -m pytest` (unele teste vorbesc cu Ollama pe bune, deci
durează ~30s).

## Cum se folosește

- La fiecare mesaj sunt întrebate toate personajele, dar răspunde doar cine are ceva de spus.
  Cine n-are, scrie `PAS` — semnal care nu ajunge pe ecran și nu se salvează.
- Scrii `@Nume` (sau apeși pe personajul din bara de sus) → cine e chemat **nu are voie să
  tacă**. În timp ce scrii `@`, apare lista cu personaje: săgeți + Enter sau click.
- Nemenționații își împart 20% șansa de a fi obligați să contribuie chiar dacă n-aveau nimic de
  zis, ca discuția să nu se stingă (`PARTEA_NEMENTIONATILOR` din `backend/personaje.py`).
- Dacă un personaj scrie `@Nume` în replica lui, cel chemat răspunde imediat după și pierde și
  el dreptul de a tăcea. Nimeni nu vorbește de două ori în aceeași rundă.
- Conversația se salvează în `backend/data/conversatie.json` și e tot acolo după refresh sau
  după repornirea serverului.

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
scoate bula de pe ecran), `{"tip":"eroare","text":"..."}`.

## Memoria personajelor

Fiecare personaj primește ultimele `MESAJE_IN_CONTEXT` mesaje (vezi `backend/istoric.py`) —
toată discuția, inclusiv replicile celorlalți, care vin cu numele vorbitorului în față.
Propriile replici rămân fără prefix, ca să nu învețe să-și semneze mesajele.

Contextul se citește la rândul fiecăruia, nu la începutul rundei: al doilea vorbitor aude ce a
zis primul și îi răspunde lui, nu neapărat mie.

## Ce rămâne pentru etapa următoare

- Conversație emergentă — grupul prinde viață, de la „eu moderez" la „ele vorbesc singure".
