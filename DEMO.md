# DEMO — Consiliul CoSiMa, 5-7 minute

Scenariul de prezentare pentru sesiunea 12. Repetat de la cap la coadă pe `gemma4:e2b`, în
Chrome, pe pagina adevărată. Runda pornită de mesajul meu durează acum **6-7 secunde**, de când
nu mai sunt întrebate toate cinci (M15). Restul minutelor sunt de vorbit, nu de așteptat — vezi
„Cronometrul real" la final.

## Înainte să intru în sală

1. **Ollama pornit, cu modelul deja cald.** `ollama ps` trebuie să arate `gemma4:e2b`. Dacă nu,
   `ollama run gemma4:e2b` și apoi Ctrl+D. Nu e doar ca să nu aștept cele 12-16 secunde de
   încărcare: **încărcarea la rece pică din când în când** pe mașina asta (una din patru,
   măsurat pe 20 august), iar prima întrebare s-ar alege cu o bulă roșie. Cu modelul deja
   încărcat, riscul dispare din demo.
2. **Serverul pornit**, cu un singur pas:
   ```powershell
   cd backend
   .venv\Scripts\python.exe -m uvicorn main:app --reload
   ```
3. **O conversație lungă, pentru pasul 6.** Memoria lungă se vede abia peste `MESAJE_IN_CONTEXT`
   mesaje, deci am nevoie de o ședință veche deschisă în listă. Ședința de referință, cea cu
   AB-ul, are 101 mesaje și stă arhivată în `backend/data/conversatie.json.migrat` — dacă nu mai
   e în listă, se readuce de acolo. Verific că rândul **Ce ține minte consiliul** apare sub
   personaje; dacă nu apare, trimit un mesaj în ea și rezumatul se scrie la capătul rundei.
   Fără el, pasul 6 n-are ce arăta.
4. **Zoom la 125%** și fereastra lată — sub 900px lista de conversații devine sertar și trebuie
   deschisă din `☰`, ceea ce e un click în plus de explicat pe scenă.

## Scenariul

### 1. Cine sunt cei cinci (0:00 — 0:45)

Pagina deschisă, bara de sus. Cinci personaje, fiecare cu avatar, culoare și unghiul lui scris
sub nume: Maestra pe fidelitate fizică, Antreprenoarea pe etape și monetizare, Clienta pe ce
vede cumpărătoarea, Operatoarea pe stoc și cifre, Programatorul pe fezabilitate.

Ideea de spus: **nu e un chatbot care știe totul despre aplicație, e un consiliu cu opinii.**
Îl întreb ce să construiesc înainte să scriu cod.

### 2. Întrebarea (0:45 — 1:45)

**+ Nouă**, apoi scriu — întrebarea e §16.7 din `concept-aplicatie-miyuki.md`, unde interesele
Maestrei și ale Clientei sunt structural opuse (fidelitate contra „vreau să văd repede"):

```
§16.7 — arătăm mărgelele AB în preview, deși simularea nu iese fidelă, sau le scoatem din MVP? @Maestra @Clienta
```

Cât scriu, sub caseta de input apare rândul „Răspunde sigur: Maestra, Clienta — rar se mai bagă
și altcineva". Ăsta e momentul de explicat regula: **mențiunea e o convocare**, iar peste cei
chemați intră cel mult unul, tras la sorți.

Apoi tac și las răspunsurile să curgă. Ce se vede, măsurat la repetiție:

| | |
| --- | --- |
| Maestra | 36-44 de cuvinte: „AB-ul nu se poate simula fidel pe o mărgea fotografiată; el este o iluzie optică…" |
| Clienta | 5-9 cuvinte: „Vreau să văd doar cum arată în altă culoare." |

Vorbesc exact cele două chemate. Dacă vreau și partea de fezabilitate sau de cifre, o cer:
`@Programatorul` sau `@Operatoarea`.

Astea sunt cele trei lucruri de arătat cu degetul:

- **Conflictul.** Maestra explică de ce nu se poate; Clienta o taie scurt — nu-i pasă.
- **Energiile diferite.** Nimeni nu scrie la fel de mult. Nu e model diferit, e regulă diferită de
  lungime în system prompt-ul fiecăruia (vezi „Nivelul de energie" din `personaj-*.md`).
- **Nu s-a adunat tot consiliul.** Ceilalți trei nici măcar n-au fost întrebați.

Al treilea e cel mai bun de povestit, pentru că e o lecție, nu o funcție: întâi am încercat să-i
fac să tacă singuri, prin prompt (`PAS`). Merge la o întrebare îngustă și nu are ce filtra la una
largă — la „vreau să dezvolt o aplicație de generare tipare", subiectul le pică aproape tuturor în
domeniu, așa că răspundeau și cei fără nimic de spus, cu replici de umplutură („Sunt gata să văd
cum arată în roz." la o întrebare de fezabilitate). Un model de 2B nu poate judeca singur
relevanța, deci relevanța nu i se mai cere lui: **cine ia cuvântul se hotărăște înainte de a-l
întreba.** `PAS` a rămas ca plasă de siguranță. Câștigul, în plus: 2-3 apeluri la model în loc de
5, deci runda se termină în jumătate din timp.

### 3. Se ascultă între ei (1:45 — 2:30)

Arăt că Programatorul nu-mi răspunde mie, ci **le răspunde lor**: propune compromisul dintre ce
a zis Maestra și ce a zis Clienta. Fiecare își citește contextul la rândul lui, nu la începutul
rundei, deci al doilea vorbitor îl aude pe primul.

Dacă în rundă a apărut un `@` scris de un personaj, și mai bine: cel chemat trece în fața cozii
și răspunde imediat.

### 4. Am prioritate (2:30 — 3:15)

Cât încă scrie cineva, scriu peste el:

```
Stai — @Operatoarea, câte coduri AB avem pe stoc acum?
```

Bula pe jumătate scrisă dispare de pe ecran și **nu ajunge în istoric**, cele deja terminate
rămân, iar pe server generarea se oprește — nu se ard tokeni pentru o rundă pe care n-o mai vede
nimeni. Măsurat la repetiție: 7 bule înainte de Enter, 8 după (a mea în plus, cea neterminată
scoasă).

Asta e partea de care sunt cel mai mulțumită: **caseta nu se blochează niciodată.**

### 5. Vorbesc și fără mine (3:15 — 4:15)

Nu mai scriu nimic și aștept. După 5-20 de secunde, consiliul își dă singur cuvântul: mai vin
2-4 replici, câte una, apoi se oprește și așteaptă.

**Atenție, pasul ăsta nu e garantat.** Dacă ultima replică a fost pe un subiect îngust — cum e
tocmai AB-ul Maestrei — ceilalți chiar n-au ce adăuga și scriu `PAS`, iar pe ecran nu apare nimic.
Măsurat: patru replici autonome la rând, toate tăcute. Ca să am ce arăta, pornesc pasul ăsta după
o replică mai largă (de exemplu după cea a Programatorului), sau îl sar.

De spus cât se așteaptă: plafonul nu e prudență, e măsurătoare — după vreo 8-10 replici autonome
modelul intră în buclă și personajele se repetă. Se oprește înainte, nu după.

Și regula care se vede greu, dar merită zisă: **cât am text în caseta de input, nimeni nu
vorbește.** Nu mă întrerupe nimeni în timp ce-mi formulez întrebarea.

### 6. Ce ține minte consiliul (4:15 — 5:15)

Trec pe conversația veche, `@Maestra merita sa simulam…` — 106 mesaje. Deschid rândul **Ce ține
minte consiliul**:

```
Subiect: Imposibilitatea simulării efectului optic al AB-ului prin fotografie
Decizii: Preview-ul de culoare trebuie generat pe server; Afișarea codurilor exacte este
         esențială pentru reproducere fidelă.
```

Aici e poanta: personajele văd doar ultimele 24 de mesaje. La mesajul 106, primele 82 nu mai
există pentru nimeni — dar deciziile luate în ele **nu s-au pierdut**, s-au strâns în rândurile
astea, care intră în promptul fiecăruia. Fără ele, Maestra se putea contrazice față de ce a zis
la început și n-avea cine să observe.

De spus și limita, dacă e timp: pe un model de 2B rezumatul iese telegrafic, iar rândul cu poziția
fiecărui personaj lipsește uneori. Subiectul și deciziile — partea pentru care există — ies corect.

### 7. Refresh (5:15 — 5:45)

F5. Mă întorc **în aceeași conversație**, cu toate cele 106 mesaje. Nu la prima din listă, nu la
un ecran gol.

Totul e local: câte un fișier JSON pe conversație, în `backend/data/conversatii/`. Fără cont,
fără bază de date. Pot deschide fișierul și văd exact ce a primit modelul.

### 8. Închiderea (5:45 — 6:30)

Ce am învățat, în trei propoziții:

- **Regulile corecte în cod pot fi invizibile în practică.** Dreptul de a tăcea era scris de la
  M8 și n-a funcționat până la M10, când l-am mutat ultimul în prompt și l-am făcut imperativ.
  Diferența: 0 tăceri din 25, față de 25 din 25. Testele treceau în ambele cazuri, pentru că
  verificau mecanica, nu modelul.
- **Cifrele dintr-un comentariu se măsoară, nu se estimează.** Fiecare constantă din proiect are
  în dreptul ei ce s-a măsurat și când.
- **Un model mic te obligă să fii explicit.** Tot ce e ambiguu în prompt, iese prost pe ecran.

## Dacă modelul răspunde prost live

| Ce se întâmplă | Ce fac, pe scenă |
| --- | --- |
| Un personaj nu apare deloc și aveam nevoie de el | Nu e întrebat decât cine e ales, deci îl chem cu `@Nume`. Mențiunea e o convocare: intră garantat și n-are voie să tacă (măsurat, 0 tăceri din 15). |
| **„Consiliul n-a avut ce adăuga."** | E linia care apare când chiar n-a vorbit nimeni. O explic ca atare — nu e server picat, e răspunsul consiliului — și reformulez cu două `@`. |
| Cineva o ia razna sau se repetă | Scriu peste el. Asta **e** demonstrația de la pasul 4, doar că mai devreme: mesajul meu taie runda. |
| Bulă roșie: „modelul nu a răspuns" | O eroare a unui personaj nu oprește runda — restul merg mai departe. Cel mai des e încărcarea la rece care pică pe GPU; e reîncercată automat o dată, deci dacă tot apare, verific Ollama într-un tab: `http://127.0.0.1:8000/api/health` răspunde `model_raspunde: false` fără să cadă serverul. Motivul exact e în consola serverului. |
| Ollama a murit de tot | Repornesc `ollama serve` în alt terminal. Serverul web nu trebuie repornit, iar istoricul e pe disc. Cât se încarcă, vorbesc despre arhitectură. |
| Nu vine niciun răspuns și punctele se învârt | Aștept 20 de secunde. Dacă tot nimic, dau refresh: ce s-a terminat e în istoric, ce nu, nu. Reiau întrebarea. |
| Rămân fără timp | Sar pasul 5 (replicile autonome) — e singurul care cere așteptare pe ceas. Pașii 6 și 7 sunt scurți și se văd instant. |

Rezerva: conversația `@Maestra merita sa simulam…` are 106 mesaje reale. Dacă live nu iese nimic
bun, o deschid și arăt o discuție care a mers deja bine, plus rezumatul ei.

## Cronometrul real

Repetiție automată în Chrome, pe pagina adevărată (20 august 2026, `gemma4:e2b` pe RTX 4050):

| Pas | Măsurat |
| --- | --- |
| Pagina deschisă, cele 5 personaje în bară | 0,9-1,5s |
| Conversație nouă, goală | 0,2s |
| De la Enter până la primul cuvânt pe ecran | 2,4s |
| Runda întreagă, două personaje chemate | 2,6s (5,6-6,1s înainte de M15) |
| Runda tăiată de mesajul meu și cea nouă terminată | 4,6s |
| Fiecare replică autonomă, cu pauza ei de 5-20s | 8-23s, când nu tac toți |
| Trecerea pe altă conversație + memoria lungă deschisă | 1,6s |
| Refresh, înapoi în aceeași conversație | 0,1s |
| **Total mașină, fără replicile autonome** | **~13s** |

Adică din cele 5-7 minute, **sub un minut** e așteptare, și aproape toată e pauza dinaintea
replicilor autonome — pasul 5, singurul care depinde de ceas și primul care se taie dacă rămân
în urmă.

Repetiția se face cu `backend/.venv\Scripts\python.exe -m pytest` înainte: 216 de teste, ~28s,
inclusiv cele cinci care vorbesc cu modelul pe bune și păzesc regula de tăcere. Dacă alea trec,
personajele se poartă cum scrie aici.
