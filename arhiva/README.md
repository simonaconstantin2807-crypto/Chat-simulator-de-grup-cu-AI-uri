# Arhivă

Fișiere înlocuite de versiuni mai noi. Păstrate pentru istoric, **nu** pentru implementare.
Nimic din acest folder nu trebuie citit ca sursă de adevăr.

## `system-prompts.md`

Prima versiune a system prompt-urilor, cu toate 5 într-un singur fișier.

Înlocuit de cele 5 fișiere `personaj-*.md` din rădăcină, care sunt sursa canonică — fiecare
conține, pe lângă prompt, și `id`, avatar, culoare, temperatura recomandată și notele de testare.

Motivul mutării: blocul de reguli comune de aici avea o eroare. Zicea „alte 4 personaje:
Maestra, Antreprenoarea, Clienta, Operatoarea, Programatorul" — cinci nume, iar fiecare personaj
se regăsea pe propria listă de colegi. În fișierele `personaj-*.md` e corectat: fiecare listează
exact ceilalți patru. Dacă implementarea ar fi pornit de aici, Maestra ar fi crezut că e într-un
grup cu Maestra.

## `aplicatie-margele-document-proiect.md`

Document de proiect mai vechi (8 secțiuni) despre platforma Miyuki.

Înlocuit de `concept-aplicatie-miyuki.md` (17 secțiuni), care e rezumatul consolidat al
brainstorming-ului și singurul document de fundal la care trimite `PLAN-IMPLEMENTARE.md`.

Motivul mutării: două documente de concept care se suprapun parțial înseamnă risc ca personajele
să citeze cifre din surse care nu coincid.
