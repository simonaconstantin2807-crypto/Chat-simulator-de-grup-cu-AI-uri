# De îmbunătățit

Ce a ieșit din testarea manuală de pe 20 august 2026, în ordinea impactului. Fiecare punct e
scris ca să poată deveni direct o etapă de lucru: ce se vede, de ce se întâmplă, ce se schimbă.

Nu e o listă de bug-uri — codul face ce spun testele (216 verzi). Sunt lucruri care ies la
iveală abia când vorbești cu consiliul pe bune.

---

## 1. Modelul — `gemma4:e4b` în loc de `e2b`

**Ce se vede.** Replici corecte ca formă, goale ca fond: „Cât de multe bijuterii sunt în stoc?"
la o întrebare despre generarea de tipare. Personajele imită tiparul verbal fără să înțeleagă
când se aplică.

**De ce.** `gemma4:e2b` e felia mică a unui model care are și una mai mare. `ollama ps` arată
1.7 GB încărcați din cei 6 GB de VRAM disponibili — încape varianta mare, cu loc de rezervă.
Fișierul de 7.2 GB de pe disc conține deja parametrii pentru ea.

**Ce se schimbă.** `ollama pull gemma4:e4b`, apoi `MODEL_IMPLICIT` în `backend/ai_client.py`.
Atât. Zero modificări de arhitectură.

**Verificare.** Rulează scriptul de măsurare a tăcerii pe ambele modele și compară. Ce trebuie
să se schimbe: calitatea replicilor, rata de `PAS` la întrebări largi. Ce **nu** trebuie să se
schimbe: anularea rundei, conversațiile, replicile autonome, tratarea erorilor. Dacă se strică
ceva de acolo, e o dependență ascunsă de model și merită reparată.

Cifrele din ambele rulări intră în prezentare — comparația măsurată e partea cea mai solidă a
proiectului.

---

## 2. Personajele au unghi, dar n-au date

**Ce se vede.** Consiliul nu dă niciodată o cifră. Întrebat direct „cât durează dezvoltarea unui
simulator?", Programatorul a răspuns despre *complexitate*, nu despre durată. Operatoarea cere
insistent estimări, dar nu oferă niciuna — cere altora ce ea însăși n-are.

**De ce.** Numărate în partea de conținut a system prompt-urilor (înainte de `Reguli:`):

| Personaj | Cifre în prompt |
| --- | --- |
| Maestra | 6 |
| Antreprenoarea | 1 |
| Clienta | 1 |
| Operatoarea | 1 |
| Programatorul | 1 |

Maestra e singura care are cu ce lucra — de-asta e și singura care aduce constant exemple
concrete (DB-10 vs DB-310, finisajele). Operatoarea, al cărei rol declarat e „cifre concrete:
cantități, timpi de execuție, clase de preț", are exact o cifră în promptul ei.

`SPEC.md` §3 promite că fiecare personaj are „în system prompt-ul lui, esența conceptului din
document". În practică au unghiul, nu conținutul. Nu e o limită a modelului — e o lipsă în
sămânță. Un model mic nu inventează cifre plauzibile, dar citează bine ce i s-a dat.

**Ce se schimbă.** Fiecare `personaj-*.md` primește 4-6 fapte concrete din
`concept-aplicatie-miyuki.md`, alese pe unghiul lui: Operatoarea — clasele Standard/Premium/Lux
și ce le diferențiază, ordinele de mărime la timpii de execuție; Antreprenoarea — ce fac
PlanBead și Beadographer, etapele din §13; Programatorul — cele două motoare de recolorare din
§4, constrângerile din §12; Clienta — regula Etsy, fluxul din §3.

**Atenție la interacțiunea cu punctul 3.** Prompturile cresc, iar regulile de la final (tăcerea
și `@`) se pot dilua. Remăsoară `PAS` după, cu scriptul existent.

**Riscul de acceptat.** Cifrele din document sunt estimările tale, nu adevăruri. Personajele le
vor cita ca sigure. E în regulă cât timp știi că vorbesc din ce le-ai dat tu — dar nu le
transforma în sursă de adevăr.

---

## 3. Întrebările rămân suspendate

**Ce se vede.** Operatoarea a întrebat „Cât durează un simulator?" — întrebare limpede pentru
Programatorul — și runda s-a încheiat fără răspuns. A trebuit să reiau eu întrebarea, cu `@`.
Apoi a deschis alta („Cât costă o comandă specială?"), la fel nelegată. Nicio buclă nu se
închide, deci discuția se împrăștie.

**De ce.** `chemati_fara_raspuns()` urmărește doar mențiunile cu `@`. Fără `@`, sistemul nu vede
nicio chemare, iar prioritatea de 80% n-are pe cine prioritiza. Regula „cheamă-l cu @" există în
prompturi, dar e formulată permisiv și stă la mijlocul listei — exact problema care a făcut
`PAS` să nu prindă (0/25 măsurat), rezolvată atunci prin mutarea regulii la final și
reformularea ei imperativă.

**Ce se schimbă.** Două lucruri:

1. Regula `@` se reformulează ca cea de tăcere: imperativă, concretă, la finalul promptului.
   „Când întrebi ceva de la cineva anume, începe cu numele lui scris cu @." Se păstrează
   avertismentul să n-o folosească la fiecare replică.
2. Plasă de siguranță în cod: dacă ultima replică a unei runde se termină cu o întrebare și
   n-are nicio mențiune, runda primește un vorbitor în plus, dintre cei care n-au vorbit încă.
   O întrebare lăsată în aer la finalul rundei nu se întâmplă într-un chat real.

**Verificare.** 10 runde fără `@`, numărat de câte ori un personaj folosește `@` când întreabă
ceva.

**Notă.** Parte din efect se rezolvă și fără cod: replicile autonome vin după 5-20 de secunde și
preiau ultima replică, deci o întrebare suspendată apucă să fie ridicată — dacă nu scriu eu
peste ea între timp.

---

## 4. Reply pe un mesaj anume

**Ce lipsește.** Într-un chat de grup real, dai reply pe o replică de acum cinci mesaje și
discuția se leagă înapoi. Aici pot răspunde doar la firul curent: ce scriu eu ajunge automat
după ultima replică, iar dacă vreau să reiau ceva mai vechi trebuie să-l rescriu cu mâna.

**De ce contează mai mult decât pare.** Se leagă direct de punctul 3. Cu reply, o întrebare
suspendată o pot ridica eu, țintit, fără să reformulez. Și e singurul mecanism prin care pot
readuce în discuție ceva ieșit din fereastra de 24 de mesaje.

**Ce se schimbă.**

- În pagină: pe fiecare mesaj, o acțiune de reply. Mesajul citat apare deasupra casetei cât
  scriu, cu posibilitatea de a renunța la citare. În conversație, mesajul meu arată vizibil la
  ce răspunde, cu un click care sare la originalul citat.
- În backend: mesajul citat se salvează ca referință în istoric (id-ul mesajului la care
  răspund), nu ca text duplicat.
- În prompt: replica citată intră explicit ca lucrul la care se răspunde.

**Detaliul de arhitectură care trebuie decis.** În `replica_personajului` din `backend/main.py`:

```python
intrebare = context.pop()["content"] if context else intrebare_implicita
```

Ultima replică din chat devine întrebarea curentă. Cu reply, regula asta intră în conflict: dacă
citez un mesaj vechi, *el* trebuie să fie întrebarea, nu ultima replică. Dar regula „fiecare
răspunde ultimei replici" e din M8 și e bună — ei i se datorează momentele în care un personaj
comentează pe altul. Deci nu se înlocuiește, se completează: citarea are prioritate pentru
primul vorbitor din rundă; de la al doilea încolo rămâne regula veche, altfel toți ar răspunde
în cor aceluiași mesaj vechi.

Mesajele au nevoie de id stabil în istoric — verifică dacă îl au deja sau dacă se identifică
doar prin poziție.

---

## 5. `num_ctx` nu e setat explicit

**Ce se vede.** Nimic. Ăsta e și motivul pentru care merită rezolvat.

**De ce.** `ollama ps` arată `CONTEXT 4096`, adică implicitul modelului — `_construieste_cerere`
din `backend/ai_client.py` nu setează `num_ctx`. Estimat acum: ~500 de tokeni system prompt, 24
de mesaje în fereastră, plus rezumatul rulant deasupra — pe la 2000-2500. Încă încape.

Dar toate cresc: punctul 2 lungește prompturile, rezumatul crește cu conversația, iar fereastra
ar putea urca. Când se depășește 4096, nu apare nicio eroare — Ollama trunchiază în tăcere, iar
efectul se vede doar ca replici mai proaste. Adică exact simptomul pe care l-am petrecut zile
încercând să-l atribuim modelului.

**Ce se schimbă.** `num_ctx` setat explicit, într-o constantă cu nume, cu un comentariu care
spune de ce există. Ideal, un avertisment în log când promptul se apropie de plafon.

---

## 6. Mărunte

- **Export conversație** (markdown sau text). Util pentru prezentare și pentru a păstra o
  ședință bună în afara aplicației. Acum singura cale e captura de ecran.
- **Curățenie în Ollama.** Cele cinci modele din `arhiva/` (`maestra`, `clienta`,
  `operatoarea`, `programatorul`, `antreprenoare`) sunt tema sesiunii 8, înlocuite de
  `personaje.json` și nefolosite de aplicație. Probabil partajează straturile cu modelul de
  bază, deci nu ocupă 5 × 7.2 GB — dar tot sunt de șters, împreună cu `gemma3:270m`, rămas de
  la depanare.

---

## Ordinea recomandată

**1 → 2 → 3** înainte de orice altceva: modelul mai bun, datele în prompturi, întrebările care
se închid. Sunt cele trei lucruri care schimbă ce se vede pe ecran, și se sprijină unul pe altul
— de-asta punctul 2 cere remăsurarea tăcerii, iar punctul 5 devine relevant tocmai pentru că 2
lungește prompturile.

**4** e funcționalitate nouă, nu reparație. Merită după ce conversația e bună — un reply pe o
replică proastă tot proastă rămâne.

**5** oricând, e ieftin, și e singurul de pe listă care previne o problemă în loc s-o repare.

**6** la final, dacă mai e timp înainte de prezentare.
