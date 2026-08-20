# SPEC — Consiliul CoSiMa (Group Chat Simulator, sesiunea 7)

## 1. Viziunea

O aplicație de chat de grup în care 5 personaje AI — fiecare cu o perspectivă diferită asupra
platformei CoSiMa (simulator de bijuterii Miyuki + generator de tipare, vezi
`concept-aplicatie-miyuki.md`) — dezbat decizii de produs. Arunc o întrebare sau o decizie de
arhitectură, personajele se contrazic din unghiurile lor, iar eu văd compromisurile înainte să
încep să scriu cod cu Claude Code.

Nu e un chatbot care știe totul despre aplicație — e o simulare de consiliu consultativ, cu
personaje care au opinii, nu doar informații.

## 2. Personajele (5)

- **Maestra** — artizan Miyuki cu experiență reală. Vorbește despre culoare, finisaje,
  fidelitate fizică. Sceptică la scurtături tehnice care sacrifică realismul (ex. AB-ul care nu
  poate fi simulat fidel pe o poză). Aduce exemple concrete din meșteșug.

- **Antreprenoarea SaaS** — gândește în plan de afaceri: etape, monetizare, nume/domeniu,
  diferențiere față de PlanBead/Beadographer. Vrea ca arhitectura de azi să nu forțeze o
  rescriere mâine.

- **Clienta Etsy** — vocea cumpărătoarei finale. Nu-i pasă de motoare tehnice, vrea rapid și
  simplu. Ține minte constrângerea Etsy (fără plată directă pe traficul de acolo) și o ridică
  ori de câte ori cineva propune ceva care ar încălca-o.

- **Operatoarea de stoc** — cifre concrete: cantități, timpi de execuție, clase de preț
  (Standard/Premium/Lux). Nu acceptă placeholder-uri — cere estimări reale sau întreabă
  explicit cum se calculează.

- **Programatorul** — vocea pragmatică de fezabilitate. Explică simplu, fără jargon inutil (eu
  am cunoștințe minime de programare). Atent la ce decizii de azi ar forța rescrieri mai
  târziu (motor de preview interschimbabil, generarea sumei de plată pe server, biblioteca
  Miyuki ca modul separat) — și spune clar când ceva e prea mult pentru etapa curentă.

## 3. Cum funcționează

Chat de grup clasic: eu scriu un mesaj (o întrebare din `concept-aplicatie-miyuki.md`, de
exemplu una din secțiunea „Întrebări deschise", sau o decizie de design nouă).

Cine răspunde — ca într-un chat de grup adevărat, unde nu sare toată lumea la fiecare mesaj.
Toate personajele sunt întrebate la fiecare mesaj, dar vorbește doar cine are ceva de spus:

- **Cine are ceva de adăugat, vorbește. Cine nu, tace.** Criteriul e domeniul fiecăruia, scris
  în system prompt-ul lui: dacă mesajul nu ține de el, scrie `PAS` — un semnal care nu ajunge
  niciodată pe ecran și nu se salvează în istoric.
- **Cei chemați cu `@NumePersonaj` nu au voie să tacă.** Mențiunea e o convocare, nu o
  probabilitate.
- **Nemenționații își împart 20%** — șansa de a fi obligați să contribuie chiar dacă n-aveau
  nimic pregătit, ca discuția să nu se stingă. Zarurile se aruncă *înainte* de a-i întreba,
  tocmai ca nimeni să nu fie pus să vorbească după ce tocmai a zis că n-are ce. Procentul se
  împarte la câți sunt nemenționați, deci rămâne 20% și când consiliul crește.
- **Mențiune făcută de un personaj** — `@NumePersonaj` scris de altcineva cheamă la fel ca
  `@NumePersonaj` scris de mine: cel chemat trece în fața cozii, răspunde imediat și pierde
  dreptul de a tăcea. Nimeni nu vorbește de două ori în aceeași rundă.
- **Fără nicio mențiune, sorții obligă un singur vorbitor.** Nimeni nefiind chemat, toți ar
  putea scrie `PAS` și mesajul meu ar rămâne fără niciun răspuns pe ecran. Unul e tras la sorți
  și n-are voie să tacă; ceilalți decid fiecare pentru el. Dacă până la urmă tot n-a vorbit nimeni, pagina
  o spune într-o linie — tăcerea consiliului nu trebuie confundată cu o defecțiune.

Fiecare răspunde **ultimei replici din chat**, nu neapărat mesajului meu — al doilea vorbitor
reacționează la primul, așa cum curge o discuție reală. Restul conversației îi rămâne în
context, deci poate contrazice și ceva spus mai devreme.

Pot interveni oricând — nu aștept să se termine runda. Mesajul meu nou taie runda în curs:
replica pe jumătate scrisă dispare de pe ecran și nu se salvează, iar cele deja terminate rămân.
Nu se suprapun două runde, iar pe server generarea se oprește odată cu runda anulată.

## 3.1 Mai multe conversații

Discuțiile stau separat, ca într-o aplicație de chat: aleg una din listă și o continui din
punctul unde am rămas. Fac una nouă dintr-un buton, o redenumesc sau o șterg.

Titlul se scrie singur, din primele cuvinte ale primului meu mesaj — nu sunt obligată să-l
compun eu, dar îl pot schimba oricând, iar titlul scris de mine nu mai e înlocuit de nimic.

Fiecare conversație are istoricul ei complet separat: personajele dintr-una nu văd nimic din
alta, nici măcar în context. Conversația deschisă supraviețuiește la refresh — mă întorc unde
eram, nu la prima din listă.

Totul rămâne local, în fișiere JSON, câte unul pe conversație — le pot deschide ca să văd exact
ce a primit modelul. Fără cont, fără bază de date.

## 3.2 Ce știu personajele

Personajele nu caută informația live (fără RAG, fără tool calling) — fiecare are, în system
prompt-ul lui, esența conceptului din document și unghiul lui de interes. Nu știu tot, dar
știu suficient cât să aibă o opinie fundamentată.

## 3.3 Conversația continuă singură, cu limită

După ce se termină runda pornită de mesajul meu, discuția mai merge de la sine 2–4 replici
(numărul se trage la sorți), apoi se oprește și așteaptă. Plafonul nu e o precauție teoretică:
pe modelul local, după vreo 8–10 replici autonome personajele intră în buclă și se repetă —
discuția se oprește înainte de asta, nu după.

- **Vorbește unul singur la fiecare replică**, nu tot consiliul. Cine e chemat cu `@` și n-a
  apucat încă să răspundă are 80% șanse să ia cuvântul; restul de 20% se împarte la ceilalți.
  Cine tocmai a vorbit nu începe și replica următoare.
- **Cel ales are voie să tacă**, ca oriunde altundeva. Dacă scrie `PAS`, replica nu se pierde:
  se încearcă altcineva, dar nu la nesfârșit — sunt câteva încercări, apoi replica se consumă.
- **Cât am text în caseta de input, nimeni nu vorbește.** Se reia când trimit sau când golesc
  caseta. O replică deja începută se termină — nu dispare din mijlocul propoziției pentru că am
  atins o tastă.
- **Mesajul meu anulează** replicile rămase și pornește o rundă nouă: am prioritate și aici.
- Totul se întâmplă în conversația deschisă. Dacă trec la alta, cea părăsită tace.

Pauza dintre replici e de câteva secunde până la câteva zeci — cât să se simtă ca o discuție
care curge, nu ca o ședință care a înghețat.

## 3.4 Ce ține minte consiliul

Personajele văd ultimele câteva zeci de mesaje, nu toată ședința. Pe la al patruzecilea mesaj,
primele nu mai există pentru nimeni — iar fără nimic la mijloc, Maestra se poate contrazice față
de ce a zis la început și n-are cine să observe.

Ce iese din fereastră nu se pierde: se strânge într-un rezumat scurt, de câteva rânduri —
subiectul, deciziile luate până acum și poziția pe care a rămas fiecare. Rezumatul intră în
promptul fiecărui personaj, ca bloc fix înaintea replicilor recente și marcat ca memorie, nu ca
replică din chat. Se actualizează din mers: la fiecare rescriere pleacă spre model doar replicile
care tocmai au ieșit din fereastră, plus rezumatul de până atunci, nu ședința de la capăt. Se
reface la capătul unei runde, nu la fiecare mesaj — acolo nu așteaptă nimeni un cuvânt pe ecran.

Rezumatul stă în fișierul conversației, ca și mesajele, deci e tot acolo după restart, și e al ei:
o conversație nu vede memoria alteia. Îl citesc în pagină, într-un rând pliabil sub personaje —
„Ce ține minte consiliul" — fără să deschid fișierul.

Pe modelul local iese folosibil, dar telegrafic: prinde subiectul și ține minte deciziile, iar
rândul care îmi atribuie mie o poziție e uneori doar ultima mea întrebare. Deciziile — partea
pentru care există — sunt corecte.

## 4. Vibe-ul

Dezbatere serioasă, dar prietenoasă — consultanță reală, nu ceartă de dragul conflictului.
Fiecare personaj vine cu argumente concrete, legate de document, nu cu generalități vagi. Ideal
ies din conversație cu o decizie sau cel puțin cu compromisurile puse clar pe masă — iar decizia
rămâne scrisă, în rezumatul de la 3.4, nu doar undeva în josul discuției.
