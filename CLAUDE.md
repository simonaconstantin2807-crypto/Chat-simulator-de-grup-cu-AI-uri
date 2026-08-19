# CLAUDE.md — convențiile proiectului

Consiliul CoSiMa: chat de grup cu 5 personaje AI, backend FastAPI + Ollama local, frontend
o singură pagină statică. Viziunea e în `SPEC.md`, etapele în `PLAN-IMPLEMENTARE.md`, modul
de folosire în `README.md`.

Regulile de mai jos nu sunt preferințe noi — sunt ce se respectă deja în cod. Se citesc
înainte de prima modificare.

## Ordinea de citit

`SPEC.md` → `PLAN-IMPLEMENTARE.md` → cele 5 fișiere `personaj-*.md` → `concept-aplicatie-miyuki.md`
(document de fundal: subiectul pe care personajele îl dezbat, nu funcționalitate de construit).

`arhiva/` conține versiuni înlocuite. **Nu e sursă de adevăr și nu se citește.**

## Test driven development

Testul se scrie **înainte** de cod. Fără excepție, inclusiv pentru un fix de o linie.

Testele descriu **comportament**, nu implementare. Un test bun rămâne verde dacă rescriu
funcția pe dinăuntru și pică doar dacă aplicația se poartă altfel.

Numele testului e o propoziție în română care spune ce trebuie să se întâmple, cu aceeași
terminologie ca în `PLAN-IMPLEMENTARE.md` și `SPEC.md` (mențiune, obligat, tace, PAS, rundă,
consiliu, context). Se citesc ca specificație:

```
test_cine_tace_nu_lasa_urma_in_istoric
test_mentionatul_nu_are_voie_sa_taca
test_fiecare_raspunde_ultimei_replici_din_chat
test_nementionatii_impart_intre_ei_douazeci_la_suta
test_procentele_se_recalculeaza_cand_adaug_personaje
```

Nu `test_ordinea_vorbitorilor_returneaza_lista` — asta descrie funcția, nu comportamentul.

Restul stilului, așa cum e deja în `backend/tests/`:

- Docstring pe test **doar când numele nu poate duce tot înțelesul**, și atunci spune *de ce*
  contează regula sau din ce cerință vine: `"""Punctul 4 din definiția de „gata": un personaj
  comentează ce a zis alt personaj."""`
- Arrange / act / assert despărțite prin linie goală. Assert-uri puține și la obiect.
- Helper-ele din fișierul de test încep cu `_` și au și ele nume în română: `_zaruri`,
  `_toti_tac`, `_model_fals`, `_istoric_izolat`, `_vorbitori`, `_consiliu`, `_sorti`.
- Aleatorul se injectează, nu se sămânțează pe ascuns: `obligati_sa_raspunda(..., sansa=)` și
  `main.zaruri`. Un test care depinde de zaruri reale e un test stricat.
- Nimic hardcodat pe consiliul de azi: se testează cu `len(main.PERSONAJE)` sau cu un consiliu
  fabricat (`_consiliu(9)`), ca regulile să rămână valide când apar personaje noi.
- Istoricul se izolează pe `tmp_path` cu `monkeypatch`. Un test nu are voie să scrie în
  `backend/data/`.

## Testele care vorbesc cu modelul

Cele care cheamă Ollama pe bune sunt marcate `@pytest.mark.ollama` (marker declarat în
`backend/pytest.ini`, cu `--strict-markers`, deci un marker scris greșit pică imediat).

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -m "not ollama"   # ~1s, 73 teste, nu cere Ollama pornit
.venv\Scripts\python.exe -m pytest                   # tot, inclusiv modelul (~30s)
```

În lucru se rulează varianta rapidă. Suita întreagă se rulează înainte de a declara o etapă
gata — un test care lovește modelul real e singura dovadă că streamingul, plafonul de tokeni
și preîncărcarea chiar funcționează.

Test nou care apelează modelul → primește marker. Test nou care poate fi determinist (model
fals prin `monkeypatch`, ca `_model_fals` din `test_main.py`) → **se scrie determinist**,
nu marcat.

## Pornire

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Apoi <http://127.0.0.1:8000>. Cere Ollama pornit, cu modelul din `ai_client.MODEL_IMPLICIT`
descărcat. Un singur pas — punctul 1 din definiția de „gata". Dacă o schimbare adaugă un al
doilea pas obligatoriu, e o schimbare greșită.

## Limba

Română peste tot: cod, nume de funcții și variabile, comentarii, docstring-uri, teste,
documentație, mesaje de commit.

Numele de funcții sunt în română, `snake_case`: `incarca_personaje`, `ordinea_vorbitorilor`,
`obligati_sa_raspunda`, `gaseste_mentiuni`, `context_pentru`, `fara_pas`,
`elimina_prefix_nume`, `salveaza_mesaj`. Constantele la fel: `MESAJE_IN_CONTEXT`,
`PARTEA_NEMENTIONATILOR`, `SEMNAL_PAS`, `INDEMN_OBLIGAT`, `CAMPURI_PUBLICE`.

Diacriticele au o regulă simplă, deja respectată:

- **Fără diacritice** în cod și în comentariile/docstring-urile Python — rămân ASCII.
- **Cu diacritice** în tot ce ajunge în fața utilizatoarei (`INDEMN_OBLIGAT`, textele din
  `static/index.html`, `systemPrompt`-urile din `personaje.json`), în datele de test
  („bună ziua", „Ce zici de AB?") și în fișierele `.md`.

Cheile JSON din `personaje.json` și din răspunsurile API sunt `camelCase` (`personajId`,
`culoareFundal`, `temperaturaRecomandata`, `systemPrompt`), pentru că le citește și
frontendul. Python-ul rămâne `snake_case`.

## Comentariile explică DE CE, nu CE

Codul spune deja ce face. Comentariul e pentru motivul care nu se vede: ce s-a încercat, ce
a mers prost, ce măsurătoare a decis valoarea, de ce nu se schimbă înapoi.

Modelul e comentariul despre `num_gpu` din `backend/ai_client.py`: spune unde stătea
workaround-ul, ce bug îl cerea (versiune, eroare exactă, dată), că bug-ul e rezolvat și
verificat, și de ce nu trebuie reintrodus — cu cifrele care o dovedesc (5.57 GB RAM și ~98s
pe CPU, crash-uri în rafală, față de 1.59 GB VRAM și 12–16s pe GPU).

La fel `KEEP_ALIVE` (12.22s la rece vs 0.87s la cald), `GANDIRE` (~3s în loc de ~17s până la
primul cuvânt), `MESAJE_IN_CONTEXT` (de ce 24 și nu 12, de când personajele se aud între ele).

Cifrele dintr-un comentariu se măsoară, nu se estimează, și se datează când vin dintr-un
context care se schimbă (versiune de Ollama, driver, GPU). Când reverifici, actualizezi
comentariul cu noua măsurătoare — nu adaugi unul nou dedesubt.

Nu se scriu comentarii care repetă linia (`# incarca personajele` peste
`incarca_personaje()`).

## Documentația se mișcă odată cu codul

`PLAN-IMPLEMENTARE.md`, `SPEC.md` și `README.md` se actualizează **în aceeași etapă** cu
codul, nu într-o trecere de curățenie ulterioară.

Niciunul n-are voie să promită ceva ce codul nu face. Concret:

- `SPEC.md` descrie comportamentul actual, la prezent. Ce nu e implementat stă la „ce rămâne
  pentru etapa următoare", nu în descrierea funcționării.
- `PLAN-IMPLEMENTARE.md` ține istoria etapelor. O etapă depășită de alta rămâne scrisă, dar
  marcată (vezi M5: **Depășit de M7**) — nu se șterge și nu se rescrie ca și cum n-ar fi fost.
- `README.md` ține pornirea, comenzile de test, tabelul de API și forma evenimentelor NDJSON.
  Dacă se schimbă o rută sau un tip de eveniment, se schimbă în README în același pas.
- Constantele citate în documentație se citează pe nume, cu fișierul lor
  (`MESAJE_IN_CONTEXT` din `backend/istoric.py`), nu prin valoare copiată — valoarea se
  schimbă, referința nu.

## Definiția de „gata"

Cele 6 puncte sunt în `PLAN-IMPLEMENTARE.md`. Punctul 6 e o regulă de igienă permanentă:

**Niciun `TODO`, `FIXME`, `XXX`, cod comentat, print de depanare, fișier de probă sau harness
de test uitat în proiect.** Ce nu se face acum, nu se lasă marcat în cod — se scrie în
`PLAN-IMPLEMENTARE.md`, la etapa unde îi e locul. Experimentele se fac în scratchpad, în afara
proiectului.

## Ce e în afara scopului

Nu se implementează, nici măcar „pregătitor", fără o decizie separată:

- **Fără cont/login.** Există o singură utilizatoare, hardcodată (`UTILIZATOR` din
  `backend/main.py`). Disputa e deja rezolvată în `personaj-programatorul.md`.
- **Fără RAG**, fără căutare live în `concept-aplicatie-miyuki.md`. Ce știu personajele e ce
  scrie în system prompt-ul lor, atât.
- **Fără tool calling.**
- Fără arbitru care citește runda și împarte cuvântul; fără personaje care scriu nechemate,
  între mesajele mele. Orchestrarea „deșteaptă" a intrat la M8 doar în forma ei simplă:
  fiecare decide pentru el, prin `PAS`.

O propunere care cere una dintre astea se discută întâi, nu se începe.

## Detalii care se rup ușor

- `PAS` nu ajunge niciodată pe ecran și nu se salvează în istoric. Se filtrează în **stream**
  (`fara_pas`), nu după ce s-a strâns răspunsul întreg — altfel apare și dispare sub ochii
  utilizatoarei. La fel prefixul `Maestra:` (`_curata_stream`).
- Contextul se citește **la rândul fiecăruia**, nu la începutul rundei. Fără asta, al doilea
  vorbitor nu-l aude pe primul și se pierde punctul 4 din definiția de „gata".
- În context, replicile altora poartă numele vorbitorului în față; replicile proprii rămân
  curate, ca modelul să nu învețe să-și semneze mesajele.
- Profilul public nu scurge `systemPrompt` (`CAMPURI_PUBLICE` din `backend/personaje.py`).
- Personajele se configurează în `personaje.json`, nu în cod. Fișierele `personaj-*.md` sunt
  sursa de conținut pentru system prompt-uri, nu formatul de rulare.
- Zarurile se aruncă **înainte** de a întreba personajul, ca să nu ajungem să cerem o replică
  de la cineva care tocmai a spus că n-are nimic de adăugat.
- O eroare a unui personaj nu oprește runda: se trimite `{"tip":"eroare"}` și se merge mai
  departe.
