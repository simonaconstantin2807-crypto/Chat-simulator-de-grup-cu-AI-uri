# Aplicație de gestiune și generare tipare mărgele Miyuki
## Document de proiect — idei consolidate (iulie 2026)

## 1. Viziune

Aplicație pentru **creatori care produc și vând** bijuterii din mărgele (nu doar hobbyiști): gestiunea stocului de mărgele pe tipuri, culori și coduri, cu generare de tipare **condiționată de stocul disponibil**. Diferența față de piață: toate aplicațiile existente merg în direcția tipar → listă de cumpărături; noi mergem invers: stoc → ce pot crea cu ce am.

**Public țintă:** creatori handmade care vând (Etsy, târguri, Instagram), gândire de producție, nu doar de hobby.

## 2. Analiza concurenței (verificată iulie 2026)

| Aplicație | Ce face | Ce lipsește |
|---|---|---|
| **MIYUKI Photo Converter** (ch1.miyuki-beads.co.jp, gratuit) | Imagine → tipar peyote/square, word chart, listă culori + cantități, PDF. Max 370×370 mm. | Interfață datată, fără cont, fără stoc, fără AI |
| **PlanBead** (Alexander Monneret, dev individual, pe piață din ~iul. 2025; ~19k descărcări Android, creștere rapidă) | Inventar mărgele, paletă Delica completă, peyote/loom/brick, word chart, mod de țesere interactiv, 3D preview, AI imagini, conversie imagine→tipar. Abonamente + "Gems". | NU generează tipare condiționate de stoc; rating 3,8 pe Android = frustrări existente |
| **Beadographer** (web, $14.99/an) | Editor tipare, colecții de mărgele proprii ca paletă | Fără cantități/fezabilitate |
| **Beadloo** (web, early-access, echipă de 2, Elveția) | Editor, urmărire mărgele per design, PDF cu logo propriu (Pro) | Inventar incipient, fără stoc-condiționat |
| **Loomerly** (iOS/Mac, plată unică) | Imagine → tipar loom/peyote/brick, palete Miyuki/Toho/Preciosa, date magazin în PDF | Fără gestiune de stoc |
| **Craftybase** | Gestiune business (stocuri, COGS, prețuri) | Zero generare de tipare |

**Concluzie:** nimeni nu răspunde la întrebarea „Ce pot face cu stocul meu?" — acesta e golul nostru.

## 3. Funcționalitatea-cheie: generare condiționată de stoc

Nu e nevoie de bază de tipare predefinite. Un singur pipeline algoritmic, cu trei surse de imagine interschimbabile:

**Pipeline:** sursă imagine → redimensionare la grilă (Canvas API) → cuantizare de culoare DOAR pe paleta din stoc (distanță Delta E în spațiul LAB) → constrângere de cantitate (dacă stocul unei culori se epuizează, alocă următoarea cea mai apropiată; ideal alocare globală: culorile rare merg în zonele de detaliu) → dithering opțional (Floyd-Steinberg) pentru palete sărace → output: grilă vizuală + word chart + verificare fezabilitate.

**Surse de imagine:**
1. Upload de la utilizator (MVP, front-end pur)
2. Generare procedurală: dungi, romburi, zigzag, gradiente, motive simetrice din culorile stocului, proporționate după cantități; reguli de bun-gust (simetrie, max 5-6 culori, contrast minim) — geometricele sunt cele mai vândute la peyote
3. Generare AI din prompt (faza cu back-end; cheia API protejată pe server)

**Funcții derivate:**
- Fezabilitate: „tiparul cere 2197 buc. DB-10, ai ~1800 → lipsesc 4 g" + listă de cumpărături doar pentru diferență
- Scădere automată din stoc la finalizarea proiectului
- Sugestii: „cu stocul actual poți face 3 brățări din tiparele salvate"
- Import stoc din PDF-ul generat de convertorul Miyuki (pagina de legendă are formatul perfect: cod DB + cantitate + greutate)

## 4. Asistentul de potrivire a culorilor (color harmony assistant)

Rezolvă ciclul frustrant „încerc combinații până iese". Teoria culorilor e algoritmizabilă (spațiul HSL, nuanța ca unghi 0-360°):
- Reguli de armonie: complementare (~180°), analoge (±30°), triadice (120°), monocromatic, split-complementary
- Verificări practice: contrast de luminozitate între vecine (lecția DB-10 vs DB-310 — două negruri aproape identice, greu de distins la lucru), regula 60-30-10 (dominantă + accente), max 5-6 culori

**Trei moduri de folosire, toate din stoc:**
1. **Verificare:** aleg 4 culori → scor de armonie + explicație + alternativă din stoc
2. **Sugestie:** aleg o culoare de pornire → 3-4 palete armonioase doar din stoc, sortate după cantitate
3. **Inspirație:** palete pe stiluri (pastel, boho, contrast, toamnă) definite ca intervale saturație/luminozitate

**Diferențiator suplimentar:** armonia FINISAJELOR (mat, lucios, metalizat, AB, transparent, silver-lined — codificate în codul DB). Două culori armonioase pe ecran pot arăta nepotrivit fizic dacă finisajele se bat. Nimeni nu face asta bine.

**Fluxul complet unic pe piață:** alege culoarea → palete armonioase din stoc cu cantități suficiente → generează tiparul → scade din stoc.

## 5. Cunoștințe de domeniu acumulate

- **Delica 11/0**: standardul; ~1,6 mm lățime; ac nr. 10-12; fir KO/Miyuki/FireLine
- **Formatul de tipar standard** (referință: PDF Miyuki): grilă vizuală + word chart pe rânduri (ex. rând 1: A4, B1, C1, D2... = culege 4×A, 1×B...) + legendă litere→coduri DB cu cantități și greutăți
- **Peyote even-count**: rândurile 1-2 se înșiră împreună; de la rândul 3 se țese decalat; direcția alternează; word chart-ul e deja în ordinea de lucru
- **Exemplu real de proiect**: 38 coloane × 237 rânduri ≈ 5,5-6 cm × 35-38 cm, >5.000 mărgele, ~23 g
- La cumpărare: +10-15% peste cantitățile din tipar; greutățile din PDF sunt orientative

## 6. Idei de diferențiere (backlog)

- Specificarea dimensiunilor în NUMĂR de mărgele, nu în mm (UX superior convertorului Miyuki)
- Editare inteligentă post-conversie / curățare tipar asistată (frustrare cunoscută la tool-urile existente)
- Marketplace pentru vânzarea tiparelor între creatori
- Localizare română + limbi est-europene (tool-urile existente sunt exclusiv în engleză)
- Urmărirea rândurilor în timpul lucrului (există la Miyuki și PlanBead — de egalat)

## 7. Plan pe etapele cursului de Vibe Coding

**Partea 1 (front-end):** proiect ales: pagina broker (soțul). Punte de învățare pentru mărgele: formulare complexe, validare, localStorage, logică de calcul în JS — de făcut temeinic, nu decorativ.

**Partea 2-3 (back-end):** aplicația de mărgele, construită direct cu conturi, stoc sincronizat, generare AI. MVP posibil de testat și front-end only: inventar în localStorage + imagine→grilă constrânsă de stoc + fezabilitate.

**De făcut între timp:**
- Folosit PlanBead ca utilizator real (gratuit întâi; abonament abia la faza de specificație): un tipar real + stocul ținut în el câteva săptămâni
- Jurnal: ce mi-a plăcut / ce m-a enervat / ce lipsește
- Citit recenziile de 1-3 stele PlanBead pe Google Play (caiet de sarcini gratuit)
- Fiecare combinație de culori reușită manual = caz de test pentru algoritmul de armonie
- Atenție: inspirație din concepte, nu copiere de interfață/nume distinctive (MatchBead™ etc.)

## 8. Model de business (schiță)

- Concurența validează: abonamente $15/an (Beadographer) până la abonamente + monedă virtuală (PlanBead); piață în creștere activă
- Fereastra de oportunitate e reală dar nu eternă — PlanBead livrează update-uri constant
- Ținta: segmentul de producție/vânzare, nu hobby — dispus să plătească pentru economie de timp și materiale
