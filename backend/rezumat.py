"""Memoria lunga a consiliului: ce iese din fereastra de context se strange intr-un rezumat.

`MESAJE_IN_CONTEXT` tine ultimele mesaje; la al patruzecilea, primele saisprezece nu mai exista
pentru nimeni, iar Maestra se poate contrazice fata de ce a zis la inceputul sedintei fara ca
cineva sa aiba cum observa. Rezumatul e ce ramane din ele: subiectul, deciziile si pozitia
fiecaruia - adica exact ce cere scopul din SPEC.md, „ies din conversatie cu o decizie".

Se actualizeaza incremental: secretarul primeste rezumatul de pana acum plus doar replicile care
tocmai au iesit din fereastra, nu toata sedinta de la capat. Altfel apelul ar creste la fiecare
runda, iar pe un model local se simte.

Modelul mic nu tine formatul singur, deci nu i se cere sa-l tina: se cere structura rigida
(`Subiect:` / `Decizii:` / `Nume: pozitia`), iar ce iese pe langa ea se taie determinist in
`scurteaza`. Masurat pe gemma4:e2b, pe o sedinta reala de 101 mesaje: raspunsul brut avea intre
5 si 14 randuri si repeta acelasi personaj de doua-trei ori, cu pozitii diferite.
"""

from ai_client import MODEL_IMPLICIT, trimite_mesaj
from istoric import MESAJE_IN_CONTEXT, incarca_istoric, rezumatul, salveaza_rezumat
from personaje import incarca_personaje

# Cate replici se aduna in afara ferestrei inainte sa se rescrie rezumatul. Un apel in plus la
# fiecare mesaj s-ar simti: pe gemma4:e2b rescrierea dureaza 2-4s (14s la primul, cu modelul rece).
# Sase e o runda de consiliu intreg - mesajul meu plus cinci replici - deci memoria se reface
# cam o data pe runda, la capatul ei, cand nu asteapta nimeni un token.
MESAJE_PE_REZUMAT = 6

# Cat de lung poate fi rezumatul care intra apoi in contextul fiecaruia. Doua randuri fixe
# (`Subiect:`, `Decizii:`) plus cate unul pentru fiecare din cele cinci personaje si pentru mine
# inseamna opt; peste atat, modelul se repeta.
RANDURI_REZUMAT = 8

# Un rand care trece de atat nu mai e o pozitie, e o replica intreaga copiata din sedinta.
LITERE_PE_RAND = 240

# Cat i se lasa secretarului sa scrie. La 300 masurat, ultimul rand iesea din cand in cand taiat
# la mijloc de cuvant (o data la opt rescrieri); se repara singur la rescrierea urmatoare, dar
# nu e niciun motiv sa fie asa de strans.
MAX_TOKENI_REZUMAT = 360

# Un proces-verbal nu se inventeaza. Personajele au 0.3-0.8, dupa temperament; secretarul n-are.
TEMPERATURA_REZUMAT = 0.2

CAP_SUBIECT = "Subiect"
CAP_DECIZII = "Decizii"

# Antetul care marcheaza memoria in prompt. Fara el, rezumatul se citeste ca ultima replica din
# chat si personajul ii raspunde ca si cum tocmai ar fi spus-o cineva.
ANTET_REZUMAT = "[Ține minte, din ședința de până acum:]"

SISTEM_REZUMAT = (
    "Ești secretarul unui consiliu consultativ. Scrii procesul-verbal al ședinței, "
    "pe scurt și la obiect. Nu participi la discuție și nu ai opinii."
)

# Cele doua plafoane din sablon vin din masuratori pe gemma4:e2b, nu din prudenta. Fara „cel
# mult trei", randul `Decizii` aduna tot: la a saptea rescriere avea vreo nouazeci de cuvinte si
# manca bugetul de tokeni al restului. Fara „adunat", in schimb, modelul ingheata prima decizie
# si nu mai adauga niciodata alta - adica exact ce trebuia sa rezolve etapa asta.
SABLON_REZUMAT = """REZUMATUL DE PÂNĂ ACUM:
{vechi}

REPLICI NOI:
{noi}

Rescrie rezumatul ca să cuprindă și replicile noi. Exact această formă:

Subiect: <ce s-a discutat, cu subiectul cel mai recent la urmă, un singur rând>
Decizii: <ce s-a hotărât, cel mult trei, cele mai importante; „nimic încă" dacă nu s-a hotărât nimic>
<Nume>: <pe ce poziție a rămas, cel mult zece cuvinte>

Un singur rând pentru fiecare nume, cel mult {nume} nume. Nu repeta un nume.
Doar rândurile astea. Fără introducere, fără concluzie, fără explicații."""

FARA_REZUMAT = "(încă nimic)"


def bloc_pentru_prompt(id_conversatie: str) -> str:
    """Memoria conversatiei, gata de lipit la coada system prompt-ului. Sir gol cat timp nu exista.

    Merge in system prompt, nu in lista de mesaje, desi e tot „un bloc fix inaintea replicilor
    recente". Motivul e masurat pe gemma4:e2b, care n-are rol `system` nativ: Ollama lipeste
    system prompt-ul de primul mesaj `user`, deci un bloc pus in fata contextului ar ingropa la
    mijlocul acelui prim mesaj tocmai ce trebuie sa fie ultimul - regula de tacere si
    `INDEMN_OBLIGAT` (vezi M10, unde ordinea a facut diferenta intre 0/25 si 25/25).

    Se vede in cifre. „Clienta, chemata pe nume, pe un subiect strain" - deci obligata sa
    raspunda - a tacut, la 15 rulari: 0/15 fara memorie, 14/15 cu blocul primul in context,
    9/15 cu el ultimul in context, 1-3/15 asa cum e acum. Celelalte doua reguli raman neatinse:
    pe subiect strain, nechemata, tot 15/15 taceri; pe domeniul ei, tot 0/15.

    Si formularea antetului conteaza, in aceeasi masura. „[Rezumatul sedintei de pana acum. Nu e
    o replica din chat - tine minte ce scrie aici:]" pare mai limpede, dar duce inapoi la 13/15:
    din tot ce se scrie dupa rol, un model de 2B retine mai ales ultima propozitie, iar una care
    contine „Nu" trage catre tacere. De aceea antetul e scurt si afirmativ. Masurat pe
    gemma4:e2b, 20 august 2026.
    """
    text, _ = rezumatul(id_conversatie)
    return f"\n\n{ANTET_REZUMAT}\n{text}" if text else ""


def de_rezumat(mesaje: list[dict], pana_la: int, fereastra: int = MESAJE_IN_CONTEXT) -> list[dict]:
    """Replicile care au iesit din fereastra de context si inca n-au intrat in rezumat.

    Ce e inca in contextul fiecaruia nu se rezuma: s-ar auzi de doua ori, o data ca memorie si
    o data ca replica.
    """
    return mesaje[pana_la : max(len(mesaje) - fereastra, pana_la)]


def _replici(mesaje: list[dict]) -> str:
    """Sedinta asa cum o citeste secretarul: fiecare rand cu numele vorbitorului in fata."""
    return "\n".join(f"{mesaj.get('nume') or 'Cineva'}: {mesaj['text']}" for mesaj in mesaje)


def scurteaza(brut: str, nume_valide: set[str]) -> str:
    """Ce ramane din raspunsul modelului: subiectul, deciziile si cate o pozitie de om.

    Pastreaza ultima pozitie a fiecaruia - cand modelul scrie acelasi nume de doua ori, a doua
    oara e cea de acum. Ordinea randurilor ramane cea in care au aparut numele, ca rezumatul sa
    nu se rearanjeze sub ochii mei la fiecare rescriere.
    """
    subiect = decizii = None
    pozitii = {}

    for rand in brut.splitlines():
        rand = rand.strip().lstrip("-*• ").strip()
        if ":" not in rand:
            continue

        cap, restul = rand.split(":", 1)
        cap, restul = cap.strip().strip("*_ "), restul.strip()[:LITERE_PE_RAND]
        if not restul:
            continue

        if cap.lower().startswith(CAP_SUBIECT.lower()):
            subiect = subiect or f"{CAP_SUBIECT}: {restul}"
        elif cap.lower().startswith(CAP_DECIZII.lower()):
            decizii = decizii or f"{CAP_DECIZII}: {restul}"
        elif cap in nume_valide:
            pozitii[cap] = f"{cap}: {restul}"

    randuri = [rand for rand in (subiect, decizii) if rand] + list(pozitii.values())
    return "\n".join(randuri[:RANDURI_REZUMAT])


def cere_rezumat(
    vechi: str, mesaje: list[dict], nume_valide: set[str], model: str = MODEL_IMPLICIT
) -> str:
    """Rezumatul rescris, deja curatat. Sir gol daca din raspuns n-a ramas nimic folosibil."""
    cerere = SABLON_REZUMAT.format(
        vechi=vechi or FARA_REZUMAT, noi=_replici(mesaje), nume=len(nume_valide)
    )
    brut = trimite_mesaj(
        cerere,
        model=model,
        sistem=SISTEM_REZUMAT,
        temperatura=TEMPERATURA_REZUMAT,
        max_tokeni=MAX_TOKENI_REZUMAT,
    )
    return scurteaza(brut, nume_valide)


def _nume_din_sedinta(mesaje: list[dict]) -> set[str]:
    """Cine are voie sa apara in rezumat: consiliul de azi si oricine a vorbit in sedinta.

    Consiliul se ia din `personaje.json`, nu din istoric: un personaj care inca n-a apucat sa
    vorbeasca poate fi totusi pomenit de secretar. Din istoric vin numele mele si ale
    personajelor iesite intre timp din consiliu, ca pozitia lor sa nu dispara la rescriere.
    """
    din_consiliu = {personaj["nume"] for personaj in incarca_personaje().values()}
    return din_consiliu | {mesaj["nume"] for mesaj in mesaje if mesaj.get("nume")}


def actualizeaza_rezumat(id_conversatie: str) -> str | None:
    """Reface memoria conversatiei, daca s-a strans destul in afara ferestrei.

    Intoarce rezumatul nou, sau `None` cand n-a fost nimic de facut - pagina afla asa daca
    memoria consiliului s-a schimbat.

    O eroare de model sau un raspuns din care nu ramane nimic nu strica ce se tinea deja minte:
    lotul ramane nerezumat si se incearca din nou la runda urmatoare. Un consiliu care isi uita
    deciziile pentru ca Ollama a clipit ar fi mai rau decat unul fara memorie lunga.
    """
    mesaje = incarca_istoric(id_conversatie)
    vechi, pana_la = rezumatul(id_conversatie)

    lot = de_rezumat(mesaje, pana_la)
    if len(lot) < MESAJE_PE_REZUMAT:
        return None

    try:
        nou = cere_rezumat(vechi, lot, _nume_din_sedinta(mesaje))
    except Exception as eroare:
        print(f"[avertisment] rezumatul nu s-a putut reface: {eroare}")
        return None

    if not nou:
        return None

    salveaza_rezumat(id_conversatie, nou, pana_la + len(lot))
    return nou
