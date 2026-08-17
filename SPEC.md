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

Cine răspunde:

- **Fără nicio mențiune** — răspund toate cele 5, ca într-o ședință de consiliu convocată
  integral.
- **Cu `@NumePersonaj`** — cine e chemat pe nume răspunde întotdeauna (mențiunea e o convocare,
  nu o probabilitate). Ceilalți își împart între ei 20% șansa de a interveni neinvitați:
  fiecare tace sau se bagă independent, deci în medie o intervenție la 5 mesaje. Procentul se
  împarte la câți sunt nemenționați, deci rămâne 20% și când consiliul crește.
- **Mențiune făcută de un personaj** — dacă cineva scrie `@NumePersonaj` în replica lui, cel
  chemat răspunde în aceeași rundă, la replica ce l-a chemat. Lanțul ține un singur val
  suplimentar, iar nimeni nu vorbește de două ori în aceeași rundă.

Un personaj poate comenta ce a zis un altul, nu doar ce am zis eu. Pot interveni oricând — nu
aștept să se termine runda.

Personajele nu caută informația live (fără RAG, fără tool calling) — fiecare are, în system
prompt-ul lui, esența conceptului din document și unghiul lui de interes. Nu știu tot, dar
știu suficient cât să aibă o opinie fundamentată.

## 4. Vibe-ul

Dezbatere serioasă, dar prietenoasă — consultanță reală, nu ceartă de dragul conflictului.
Fiecare personaj vine cu argumente concrete, legate de document, nu cu generalități vagi. Ideal
ies din conversație cu o decizie sau cel puțin cu compromisurile puse clar pe masă.
