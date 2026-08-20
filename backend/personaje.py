import json
import random
import re
from pathlib import Path

PERSONAJE_PATH = Path(__file__).parent.parent / "personaje.json"

# Sansa ca la runda pornita de mesajul meu sa intre in vorba si cineva care n-a fost chemat pe
# nume. Cei mentionati raspund oricum, asa ca procentul asta nu se imparte cu ei. Pana la M15 se
# arunca un zar de fiecare tacut, cu pragul impartit la cati erau; acum se arunca unul singur
# pentru toti si se trage la sorti cine intra, deci 20% ramane 20% oricat ar creste consiliul,
# fara nicio impartire.
PARTEA_NEMENTIONATILOR = 0.2

# Cati vorbitori are runda pornita de mesajul meu cand nu e chemat nimeni pe nume. Numarul se
# trage la sorti intre plafoane.
#
# Pana la M15 erau intrebati toti cinci, iar PAS ii filtra pe cei carora subiectul le era
# strain. Filtrul asta n-are ce lucra la o intrebare larga: la „vreau sa dezvolt o aplicatie de
# generare tipare pentru bijuterii Miyuki", criteriul de domeniu se potriveste corect pentru
# aproape toti, deci raspundeau 4-5, iar cei fara nimic de spus scoteau non-sequitur din
# inventarul lor („Sunt gata sa vad cum arata in roz" la o intrebare de fezabilitate).
#
# Doi-trei e cat incape intr-un schimb de replici citibil, si costa 2-3 apeluri la model in loc
# de 5, deci runda se si termina vizibil mai repede.
VORBITORI_PE_RUNDA = (2, 3)

# Cat din replicile pe care conversatia le duce singura merg catre cine a fost chemat pe nume
# si n-a apucat inca sa raspunda. Restul de 20% se imparte la ceilalti. Aici vorbeste un singur
# personaj, ales dintre toti, spre deosebire de runda pornita de mesajul meu, unde e intrebat
# fiecare si raspunde cine are ceva de zis.
PARTEA_CHEMATILOR = 0.8

# Ce ajunge in pagina: identitatea vizuala si unghiul personajului. System prompt-ul si
# temperatura raman pe server.
CAMPURI_PUBLICE = ("id", "nume", "rol", "avatar", "culoare", "culoareFundal")

TIPAR_MENTIUNE = re.compile(r"@(\w+)")


def incarca_personaje() -> dict:
    date = json.loads(PERSONAJE_PATH.read_text(encoding="utf-8"))
    return {p["id"]: p for p in date["personaje"]}


def profil_public(personaj: dict) -> dict:
    return {camp: personaj[camp] for camp in CAMPURI_PUBLICE}


def gaseste_mentiuni(text: str, personaje: dict) -> list[str]:
    """Id-urile personajelor scrise cu @, in ordinea aparitiei si fara dubluri."""
    dupa_eticheta = {p["nume"].lower(): p["id"] for p in personaje.values()}
    dupa_eticheta.update({id_personaj.lower(): id_personaj for id_personaj in personaje})

    gasite = []
    for eticheta in TIPAR_MENTIUNE.findall(text):
        id_personaj = dupa_eticheta.get(eticheta.lower())
        if id_personaj and id_personaj not in gasite:
            gasite.append(id_personaj)
    return gasite


def _tras_la_sorti(candidati: list[str], sansa) -> str:
    """Unul dintre candidati, ales cu aceeasi aruncare injectata ca restul deciziilor.

    `sansa()` da un numar in [0, 1), dar un fals de test poate da chiar 1.0; `min` tine
    indicele in lista in loc sa lase runda sa crape.
    """
    return candidati[min(int(sansa() * len(candidati)), len(candidati) - 1)]


def _cati_vorbitori(sansa) -> int:
    """Cati iau cuvantul, tras la sorti intre `VORBITORI_PE_RUNDA`.

    `min` tine numarul sub plafon si daca un fals de test da chiar 1.0, ceea ce `random.random`
    nu da niciodata.
    """
    minim, maxim = VORBITORI_PE_RUNDA
    return min(minim + int(sansa() * (maxim - minim + 1)), maxim)


def vorbitorii_rundei(text: str, personaje: dict, sansa=random.random) -> list[str]:
    """Cine ia cuvantul la runda pornita de mesajul meu, in ordinea in care e intrebat.

    Cei chemati cu @, toti si primii: mentiunea e o convocare, nu o probabilitate. Peste ei
    intra cel mult unul nechemat, cu sansa `PARTEA_NEMENTIONATILOR` - altfel runda ar creste la
    loc la patru-cinci guri, adica exact ce trebuia sa rezolve selectia.

    Fara nicio mentiune nu e nimeni chemat, deci se trag la sorti `VORBITORI_PE_RUNDA` dintre
    toti. Nimeni nu e ales de doua ori.

    Aici nu se aplica 80/20: cei chemati sunt deja inauntru si iesiti din tragere, deci n-are
    cui da intaietate. Regula ramane cum e, unde e - la replicile pe care conversatia si le da
    singura (`alege_vorbitorul`).

    De ce selectie si nu intrebat toti, vezi `VORBITORI_PE_RUNDA`. PAS nu dispare: cine e ales
    fara sa fie obligat poate tot sa taca, si acolo ramane plasa de siguranta pentru intrebarea
    ingusta, pe care selectia n-are cum s-o judece.
    """
    alesi = gaseste_mentiuni(text, personaje)

    if alesi:
        if sansa() >= PARTEA_NEMENTIONATILOR:
            return alesi
        cati = len(alesi) + 1
    else:
        cati = _cati_vorbitori(sansa)

    while len(alesi) < cati:
        ales = alege_vorbitorul(personaje, [], exclusi=alesi, sansa=sansa)
        if ales is None:
            break
        alesi.append(ales)

    return alesi


def obligati_sa_raspunda(
    text: str, vorbitori: list[str], personaje: dict, sansa=random.random
) -> list[str]:
    """Cine, dintre cei alesi, n-are voie sa taca.

    Cu mentiune, toti cei alesi: cei chemati pentru ca mentiunea e o convocare, iar cel intrat
    pe cei `PARTEA_NEMENTIONATILOR` pentru ca l-au adus sortii, nu subiectul - daca l-am lasa
    sa se filtreze singur, n-ar mai fi nicio diferenta fata de a-l intreba degeaba.

    Fara mentiune, unul singur tras la sorti dintre cei alesi: altfel toti ar putea scrie PAS si
    mesajul meu ar ramane fara niciun raspuns pe ecran (M9). Ceilalti isi pastreaza dreptul de a
    tacea. Se trage numai dintre cei alesi - unul neales n-ar fi intrebat oricum, deci obligatia
    lui n-ar ajunge nicaieri.

    `sansa` e injectata ca testele sa nu depinda de zaruri reale.
    """
    if gaseste_mentiuni(text, personaje):
        return list(vorbitori)
    return [_tras_la_sorti(list(vorbitori), sansa)] if vorbitori else []


def chemati_fara_raspuns(mesaje: list[dict], personaje: dict) -> list[str]:
    """Cine a fost chemat cu @ si inca n-a luat cuvantul dupa aceea, in ordinea chemarii.

    O chemare se stinge in clipa in care cel chemat vorbeste - de-asta se sterge inainte de a
    citi mentiunile din replica lui, altfel un personaj care isi scrie numele si-ar da singur
    intaietate la replica urmatoare.
    """
    asteptati = []
    for mesaj in mesaje:
        vorbitor = mesaj.get("personajId")
        if vorbitor in asteptati:
            asteptati.remove(vorbitor)

        for chemat in gaseste_mentiuni(mesaj.get("text", ""), personaje):
            if chemat != vorbitor and chemat not in asteptati:
                asteptati.append(chemat)

    return asteptati


def alege_vorbitorul(
    personaje: dict,
    chemati: list[str],
    exclusi: list[str] | tuple[str, ...] = (),
    sansa=random.random,
) -> str | None:
    """Cine ia cuvantul la o replica pe care conversatia o duce singura, dupa regula 80/20.

    Cei chemati si neajunsi la cuvant iau `PARTEA_CHEMATILOR`, restul isi impart ce ramane.
    `exclusi` tine afara pe cine tocmai a vorbit - doua replici la rand de la acelasi personaj
    n-ar mai fi o conversatie de grup - si pe cine a fost deja incercat si a tacut.

    Cand una dintre cele doua grupe e goala nu se mai arunca zarul de grup: n-ar avea ce
    imparti. `None` inseamna ca n-a mai ramas nimeni de intrebat.
    """
    candidati = [id_personaj for id_personaj in personaje if id_personaj not in exclusi]
    prioritari = [id_personaj for id_personaj in chemati if id_personaj in candidati]
    ceilalti = [id_personaj for id_personaj in candidati if id_personaj not in prioritari]

    if not candidati:
        return None
    if not prioritari:
        grupa = ceilalti
    elif not ceilalti:
        grupa = prioritari
    else:
        grupa = prioritari if sansa() < PARTEA_CHEMATILOR else ceilalti

    return _tras_la_sorti(grupa, sansa)
