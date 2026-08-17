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

- Scrii un mesaj fără mențiune → răspunde tot consiliul, pe rând.
- Scrii `@Nume` (sau apeși pe personajul din bara de sus) → răspunde sigur cine e chemat, iar
  ceilalți își împart 20% șansa de a interveni neinvitați (vezi `PARTEA_NEMENTIONATILOR` din
  `backend/personaje.py`). În medie, o intervenție la 5 mesaje.
  În timp ce scrii `@`, apare lista cu personaje: săgeți + Enter sau click.
- Dacă un personaj scrie `@Nume` în replica lui, cel chemat răspunde în aceeași rundă. Lanțul
  se oprește după un val (`VALURI_MAXIME` din `backend/main.py`) și nimeni nu vorbește de două
  ori în aceeași rundă.
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
răspuns), `{"tip":"gata"}` (mesaj terminat), `{"tip":"eroare","text":"..."}`.

## Memoria personajelor

Fiecare personaj primește ultimele `MESAJE_IN_CONTEXT` mesaje (vezi `backend/istoric.py`):
mesajele mele și propriile lui replici. **Nu** vede încă replicile celorlalte personaje.

## Ce rămâne pentru etapa următoare

- Personajele se aud între ele (filtrul din `istoric.context_pentru`).
- Logica de tură: cine vorbește și când.
- Conversație emergentă — grupul prinde viață, de la „eu moderez" la „ele vorbesc singure".
