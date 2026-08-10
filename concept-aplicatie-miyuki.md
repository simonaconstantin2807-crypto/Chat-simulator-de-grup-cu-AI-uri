# Platformă Miyuki: Generator de Tipare + Simulator de Bijuterii
### Rezumat de concept — document de context pentru consiliul de AI

---

## 1. Ce este acest document

Rezumatul unui brainstorming despre o platformă web pentru brandul de bijuterii handmade **CoSiMa** (mărgele Miyuki Delica). Documentul e destinat unui consiliu de AI care va oferi consultanță pe dezvoltarea aplicației. Marchează clar **ce s-a decis deja** și **ce a rămas de clarificat** (secțiunea 16), ca discuția consiliului să se concentreze acolo unde e nevoie.

Regula de fundal a întregului proiect: **se construiește pe etape, dar arhitectura fiecărei etape trebuie gândită de la început în funcție de etapele următoare** — nicio decizie de acum să nu forțeze o rescriere mai târziu.

---

## 2. Viziunea de ansamblu

O **singură platformă cu două module majore**, pe o fundație comună:

- **Simulator** (orientat spre client) — clientul final personalizează culorile unei bijuterii pe baza unei poze reale și lansează o comandă personalizată.
- **Generator de tipare** (orientat spre creator) — transformă o imagine într-un pattern (tipar) de mărgele, care poate fi vândut ca produs digital sau folosit la execuție.

Cele două sunt fețe ale aceleiași monede: generatorul transformă imagini în pattern-uri, simulatorul transformă pattern-uri/produse în imagini.

Pe termen lung, platforma devine **produs SaaS** oferit și altor creatoare de bijuterii Miyuki, pe planuri tarifare. CoSiMa rămâne brandul de bijuterii care *folosește* platforma; platforma e o afacere separată, cu identitate proprie.

---

## 3. Modulul Simulator — fluxul de bază

**Ideea centrală:** o bijuterie (brățară, inel, cercel, pandantiv, choker) creată într-un anumit design și anumite culori Miyuki este pusă la vânzare. Pe pagina de produs, clientul poate alege să o **customizeze**: e redirecționat către simulator, unde schimbă culorile pe același design și vede rezultatul înainte de a comanda.

**Ce face creatoarea (setup per produs, o singură dată):**
1. Încarcă poze cu bijuteria (minim 2: un **close-up** pentru selectarea precisă a culorilor + o poză cu **bijuteria întreagă**; ideal 5–7 unghiuri).
2. Selectează câte culori a folosit (poate fi între **1 și 20+**).
3. Marchează pe poză fiecare culoare și introduce **codul Miyuki** aferent. Codurile rămân **editabile** ulterior.
4. Aplicația construiește automat o **mască** (o hartă a pixelilor: ce zonă = ce culoare) și o propune; creatoarea o corectează cu **pensulă/radieră** unde e nevoie.

**Ce vede clientul:**
- Poza bijuteriei + lista de culori cu codurile Miyuki.
- Schimbă un cod → poza se **recolorează instant**.
- Vede prețul recalculat live și disponibilitatea, apoi lansează comanda.

**Două moduri de customizare (pentru a nu speria clientul cu 20 de selectoare):**
- **Palete predefinite** de creatoare (ex. „variantă aurie", „variantă smarald") — devin și **argument de vânzare** („palete armonizate de designer"), rezolvând faptul că bijuteriile multicolore cer o teorie de potrivire a culorilor pe care clienții nu o au.
- **Control total** — clientul schimbă fiecare cod. Se vor customiza cel mai des bijuteriile **uni- sau puțin-colore**.

---

## 4. Inima tehnică — recolorarea (două motoare)

Nu se face randare mărgea-cu-mărgea. Preview-ul are **două motoare**, alese automat în funcție de produs:

**A. Motor foto (recolorare de fotografie)** — pentru piese cu pattern, unde poza reală e de neînlocuit.
- Nu vopsește pixelii cu culoare plată. Păstrează **luminozitatea și umbrele** fiecărui pixel și schimbă doar **nuanța** — o mărgea cu reflexie de lumină devine altă culoare cu aceeași reflexie. De aceea rezultatul arată ca o poză reală.
- Este exact tehnica pe care o folosesc manual magazinele (mască + Hue/Saturation în Photoshop); noutatea proiectului e **automatizarea ei, în browser, în timp real, în mâna clientului**.

**B. Motor generat (mărgele virtuale)** — pentru piese unicolore/simple (peyote).
- Desenează structura din mărgele virtuale (peyote e o structură regulată, ușor de randat frumos), cu luciu simulat.
- Deblochează customizarea **dimensiunilor**: la peyote unicolor, un slider de **lățime** (ex. 5/7/9/11 coloane) regenerează structura live. Extensibil ulterior la lungime/circumferință.
- Nu depinde de calitatea pozei → servește și ca **fallback** când o poză nu permite recolorare fidelă.

**Consecință de arhitectură:** preview-ul se scrie ca **motor interschimbabil**, ca un al treilea motor (ex. AI generativ, când va fi fidel structural) să se poată adăuga *alături*, fără rescriere. Motorul B este, în esență, același cod cu motorul de randare al generatorului de tipare.

---

## 5. Culori, finisaje, biblioteca Miyuki

- Clientul poate alege din **toată gama** de coduri Miyuki, nu doar din stocul creatoarei.
- **Legendă** lângă fiecare cod ales: swatch-ul oficial (imaginea mărgelei ca pe site-ul Miyuki) + toate caracteristicile (nume, finisaj, opacitate, mărime).
- **Limita de fidelitate, asumată:** **nuanța** se redă fidel; **finisajul** (matte / galvanized / AB / transparent) se poate doar **aproxima** pe poză (matte = reducem luciul; lucios = accentuăm reflexiile; transparent = creștem luminozitatea/saturația). AB-ul, fiind comportament optic, nu poate fi „inventat" fidel pe o mărgea fotografiată altfel. Se afișează mențiunea **„preview orientativ"**; swatch-ul oficial garantează detaliul real.
- Cataloagele Miyuki sunt publice; **de verificat** termenii de utilizare **comercială** înainte de SaaS (alternativă: bibliotecă proprie de swatch-uri fotografiate).

**Biblioteca Miyuki = modul separat, fundația comună a ambelor module.** Câmpuri: cod, culoare, finisaj, clasă de preț, stoc, swatch. Se construiește o dată; o folosesc și simulatorul, și generatorul, și (ulterior) un eventual asistent AI de vânzare.

---

## 6. Preț, cantități, stoc

**Preț — model cu clase (decis):** fiecare cod primește o clasă **Standard / Premium / Lux** (codurile placate cu aur/argint, galvanized etc. costă de 2–4× mai mult). Prețul afișat se **recalculează live** când clientul alege un cod dintr-o clasă superioară. Simplu de întreținut (clasă per cod, nu preț per cod).

**Cantități:** bijuteria personalizată e identică structural cu cea sursă → cantitatea totală e o constantă. Se estimează prin: numărare la creare (≈190–200 mărgele Delica 11/0 per gram) / din pattern (numărătoare exactă) / din procentul de suprafață al fiecărei zone × totalul piesei.

**Stoc:** inventar simplu per cod (grame) + **prag de siguranță** (ex. 20%). La fiecare alegere, aplicația compară necesarul cu stocul și afișează un mesaj cu **timpi de execuție diferiți**: „în stoc" vs. „culoare comandată special". La lățire/îngustare, cantitatea → prețul → stocul se recalculează automat. Necesită disciplina actualizării stocului.

*Timpii de execuție concreți nu sunt încă estimați → pornesc ca valori placeholder editabile.*

---

## 7. Modulul Studio — listări din randări (pentru creatoare)

Aceeași unealtă de recolorare, folosită de creatoare pentru **producerea de listări**, nu doar de clienți:

- Se alege produsul sursă, se setează o paletă nouă (sau mai multe deodată) → aplicația **exportă imagini la rezoluție mare**, gata de urcat pe Etsy ca listare separată de tip **„made to order"**.
- Dintr-o singură bijuterie fizică rezultă 5–10 listări virtuale → se **produce doar ce se comandă**, zero stoc blocat. (Este exact ce face manual contul de Instagram urmărit ca referință, `biju_jewelry`.)
- **Mai multe unghiuri per listare:** din pozele de la mai multe unghiuri ale sursei; după definirea paletei pe prima poză, aplicația **propune automat** măștile pe celelalte unghiuri (aceleași culori, alte zone). **Export în lot** → pachet consistent de 5–7 imagini. Sloturile Etsy se completează cu grafic de paletă (auto-generat), vizual „disponibilă și în alte culori", imagini de brand.
- Pozele **lifestyle** (purtate) sunt recolorabile, dar cer mai multă corecție manuală (pielea reflectă culoare).

**Consecință de arhitectură:** măștile se salvează la **rezoluția originală** a pozei (nu la cea de afișare), altfel exportul de listări iese la calitate mică. Un produs = o **colecție de perechi poză–mască**, cu paleta definită o dată la nivel de produs.

---

## 8. Modulul Generator de tipare și puntea cu simulatorul

Puncte de legătură între cele două module (motivul pentru care sunt o singură platformă):

1. **Biblioteca Miyuki comună** — fundația ambelor.
2. **Mască → pattern:** din poza + masca unui produs se poate deriva pattern-ul digital → fiecare bijuterie listată poate genera automat și **pattern-ul de vânzare** ca produs digital. Un produs fizic → listare + variante recolorate + pattern digital = trei fluxuri de venit din același setup.
3. **Pattern → preview:** randarea „mărgelelor virtuale" a generatorului *este* motorul generat al simulatorului.
4. **Pattern → cantități exacte** → alimentează validarea de stoc și clasele de preț.
5. **La nivel SaaS:** creatoarea încarcă poza → primește pattern → listează produsul cu simulator pentru clienți → exportă randări pentru listări virtuale. Lanț cap-coadă pe care niciun instrument existent nu-l acoperă.

---

## 9. Integrarea cu canalele de vânzare

- **Site propriu** (viitor, probabil **Merchant Pro** pentru piața din România) — permite cod custom și buton „Personalizează" pe pagina de produs. *(Se renunță la platforma Artynos.)*
- **Etsy** — platformă închisă, **fără aplicații încorporate**. Integrarea = **punte prin link**:
  - Link în descriere (afișat ca text ne-clickabil → trebuie **scurt și memorabil**, ex. `simulator.cosima.ro/nume-bijuterie`).
  - Un vizual printre poze cu 3–4 variante de culoare + „personalizabilă, link în descriere".
  - **Regula critică (fee avoidance):** e interzis să inițiezi o vânzare pe Etsy și s-o finalizezi în afara ei. Deci pentru **traficul din Etsy** simulatorul e **doar de vizualizare, fără plată** — la final clientul primește codurile alese și instrucțiunea „comandă listarea «personalizată» pe Etsy și lipește codurile în notă". Pagina pentru trafic Etsy nu conține niciun preț mai mic sau alt canal de cumpărare.
- **Social media** și **site propriu** → butonul normal de **plată Stripe**.
- **Detecția sursei traficului** (`?sursa=etsy`) → **două finaluri de comandă** din aceeași aplicație: rută „notă pe Etsy" vs. rută Stripe. *(Sursa se salvează la fiecare vizită — decizie de arhitectură din ziua 1.)*

---

## 10. Plata

Trei niveluri posibile; **ales pentru MVP: nivelul 2**.
1. **Manual** — clientul trimite configurația pe email, creatoarea cere plata separat.
2. **Link de plată (Stripe/PayPal)** — aplicația generează automat un link cu suma corectă; clientul plătește pe pagina securizată (creatoarea nu atinge datele de card), comision ~2–3% + taxă fixă mică. Clientul plătește „la cald", imediat după preview.
3. **Checkout integrat complet** — abia la volum mare / site propriu matur.

**Regulă de securitate:** generarea sumei/link-ului se face pe **server**, niciodată doar în browser (altfel suma ar putea fi modificată înainte de plată). *(Încă nu există comenzi directe.)*

---

## 11. Varianta SaaS și problema calității pozelor

Cel mai mare risc al SaaS: creatoarele au poze de calitate variabilă, imposibil de controlat. Se rezolvă **prin produs**, pe patru straturi:
1. **Verificator de poză** ca poartă de intrare — analizează imaginea la încărcare, dă scor + diagnostic („zone supraexpuse", „fundal confundabil", „culori prea apropiate"); sub prag, poza e respinsă cu sfaturi, ca preview-ul urât să nu strice reputația platformei.
2. **Ghid de fotografiere** în onboarding (tehnici de mai jos), perceput ca beneficiu al abonamentului.
3. **Unelte de corecție manuală** (pensulă/radieră de mască) — plasa de siguranță; transformă „aplicația nu merge cu pozele mele" în „aplicația m-a ajutat să repar poza".
4. **Degradare elegantă** — fallback pe motorul generat pentru poze slabe.

Calitatea asistată se poate lega de **planuri tarifare** (bază = verificator + corecție manuală; superioare = separare asistată de AI, mai multe produse/poze).

**Tehnici de fotografiere (standardul CoSiMa, și baza ghidului SaaS):** lumină **difuză** (lightbox / zi înnorată), fundal **mat neutru contrastant**, bijuteria **plată** cu camera **perpendiculară**, o **singură temperatură** de lumină + balans de alb manual, **expunere ușor scăzută** (mai bine puțin întunecat decât „ars"). Scopul realist: fiecare culoare = un interval îngust, bine separat de nuanțe (nu „exact atâtea culori câte mărgele" — imposibil fizic).

---

## 12. Frontend vs. backend

Proiectul **necesită backend**, dar modest la MVP (~**70% frontend / 30% backend**).
- **Frontend (browser):** recolorarea în timp real (canvas, local, instant), motorul generat, selectoarele, recalcularea live a prețului.
- **Backend:** datele produselor (poze, măști, coduri, cantități), stocul, comenzile, generarea link-ului Stripe, login-ul de administrare, tot ce ține de SaaS.
- **Recomandare:** Supabase sau Firebase (bază de date + stocare + autentificare gata făcute) + câteva funcții mici pentru Stripe/email. Gratuit sau câțiva dolari/lună la start, scalează spre SaaS.

---

## 13. Roadmap pe etape

- **Etapa 1 — proiect de curs** (ultima parte a cursului de Vibe Coding, IT School; **backend acceptat**).
  - **Intră:** un singur produs, setup de marcare a culorilor pe poză, **recolorare live în browser** (inima și partea cea mai impresionantă la prezentare), legenda cu codurile Miyuki, formular de comandă care trimite configurația pe email. Backend minim pe Supabase (produse + comenzi).
  - **Nu intră (rămân roadmap):** Stripe, stoc + timpi de execuție, motor generat, clase de preț, multi-creator.
  - Se construiește pe **fundația comună** (biblioteca Miyuki ca modul separat din ziua 1, măști salvate în format „traductibil" în pattern) → proiectul de curs *este* faza 1 din MVP-ul real, nu un exercițiu aruncat.
- **Etapa 2 — MVP complet:** plată Stripe, stoc + timpi de execuție, clase de preț.
- **Etapa 3:** motor generat (peyote + lățime) + modul Studio (export listări).
- **Etapa 4:** modulul Generator de tipare.
- **Etapa 5:** SaaS multi-creator (conturi, planuri tarifare, facturare, verificator avansat).

**Decizii de arhitectură din ziua 1** (chiar dacă funcționalitatea vine târziu): bază de date pregătită **multi-creator** (fiecare produs legat de un cont); **biblioteca Miyuki** ca modul separat cu câmpuri de finisaj/clasă/stoc; preview ca **motor interschimbabil**; **comanda** ca obiect de sine stătător (configurație + status); **sursa traficului** salvată; **măștile la rezoluție originală**; produsul ca **colecție de perechi poză–mască**.

---

## 14. Cum facem update-uri

Fiind aplicație web, orice îmbunătățire publicată e **instant la toți** (fără versiuni de instalat). Cu Claude Code: modifici → testezi local → publici. Discipline de la început: **cod în GitHub** (istoric + plasă de siguranță); la SaaS, **mediu de test separat** de cel „live" (Vercel + Supabase permit publicare cu un click și revenire la versiunea anterioară).

---

## 15. Analiza pieței

**Nu există o aplicație care să facă exact asta** (configurator client-facing, pe poză reală recolorată, cu coduri Miyuki). Vecini:
- **Aplicații de design Miyuki** (ex. PlanBead, Miyuki Photo Converter) — puternice, dar pentru **creator**, nu configurator pentru clientul final.
- **Configuratoare de bijuterii „fine"** (Threekit, Salsita, Doogma, Pencil) — experiența client-facing dorită (decizii live, preț și rezumat în timp real), dar pe **modele 3D**, enterprise, fără mărgele/coduri/finisaje.
- **Comunitatea Miyuki** rezolvă customizarea **manual** (galerii, mesaje pe Etsy, listări „custom order" cu note text) — exact golul de umplut.

**Concluzie:** nișa „configurator client-facing pentru bijuterii Miyuki pe poză reală" pare **liberă**, ceea ce validează și ideea SaaS. Diferențiator față de giganții 3D: soluție croită pe specificul mărgelelor (coduri, finisaje, stoc, timpi) și accesibilă ca preț. Fereastra e reală, dar nu eternă — cine ocupă nișa prima o definește.

---

## 16. Întrebări deschise (pentru consiliu)

Niciuna nu blochează startul; fiecare trebuie decisă înainte de etapa ei.
1. **Timpii de execuție** — estimări reale pentru „în stoc" vs. „la comandă".
2. **Prețuri** — cum se calculează prețul de bază al unei bijuterii și cât adaugă clasele Premium/Lux.
3. **Drepturile pe datele/swatch-urile Miyuki** — utilizare comercială (relevant la SaaS).
4. **Domeniu și nume** — domeniul propriu; **numele platformei SaaS** (distinct de CoSiMa).
5. **Livrare și retur** — curier, costuri, ambalare; politica de retur (în UE, produsele **personalizate** sunt exceptate de la dreptul de retur de 14 zile, dar trebuie specificat explicit).
6. **GDPR** — politică de confidențialitate (simplă la MVP; serioasă la SaaS, unde platforma procesează datele clienților altor creatoare).
7. **Detalii de produs** — dimensiunile de mărgele acoperite (doar Delica 11/0 sau și rounds?), limbile interfeței (RO + EN pentru Etsy), tratarea comenzilor abandonate.

---

## 17. Cum estimăm evoluția domeniului (a fi cu un pas înainte)

Direcții de fond probabile, deja anticipate de arhitectură:
- **AI generativ tot mai bun la imagini de produs** — azi exclus din preview (nefidel structural, reinventează detalii); când devine fidel, se adaugă ca **al treilea motor** (de asta preview-ul e interschimbabil).
- **Personalizarea devine așteptare standard** în e-commerce → cererea pentru exact acest produs crește; creatoarele mici caută unelte accesibile.
- **Comerțul se mută în social media** (Instagram/TikTok shopping) → aplicația web cu link propriu e nativ compatibilă.
- **Vânzare conversațională cu AI** — pas ulterior natural: un asistent care ghidează customizarea („ceva pentru o rochie verde smarald" → propune palete); **biblioteca Miyuki** structurată e combustibilul.

**Metoda practică** de a rămâne înainte nu e ghicitul, ci **ritmul**: după lansare, semnalul cel mai valoros sunt clienții reali (ce customizează, unde abandonează, ce întreabă). O **revizuire trimestrială** (schimbări în domeniu + ce spun datele aplicației) bate orice prognoză de azi.
