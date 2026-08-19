import json
import random
import re
from pathlib import Path

PERSONAJE_PATH = Path(__file__).parent.parent / "personaje.json"

# Cat din runda le ramane celor care n-au fost chemati pe nume. Cei mentionati raspund oricum,
# asa ca procentul asta nu se imparte cu ei: e sansa ca cineva sa intervina neinvitat. Se
# imparte egal la cati taciti sunt, deci ramane 20% si daca maine consiliul are noua membri.
PARTEA_NEMENTIONATILOR = 0.2

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


def ordinea_vorbitorilor(text: str, personaje: dict) -> list[str]:
    """Cine e intrebat si in ce ordine: intai cei chemati pe nume, apoi restul.

    Sunt intrebati toti - intr-un chat natural fiecare cantareste daca are ceva de zis. Cine
    n-are, tace (vezi `obligati_sa_raspunda` pentru cine n-are voie sa taca).
    """
    mentionati = gaseste_mentiuni(text, personaje)
    return mentionati + [id_personaj for id_personaj in personaje if id_personaj not in mentionati]


def _tras_la_sorti(candidati: list[str], sansa) -> str:
    """Unul dintre candidati, ales cu aceeasi aruncare injectata ca restul deciziilor.

    `sansa()` da un numar in [0, 1), dar un fals de test poate da chiar 1.0; `min` tine
    indicele in lista in loc sa lase runda sa crape.
    """
    return candidati[min(int(sansa() * len(candidati)), len(candidati) - 1)]


def obligati_sa_raspunda(text: str, personaje: dict, sansa=random.random) -> list[str]:
    """Cine trebuie sa contribuie, chiar daca n-avea nimic pregatit.

    Cei chemati cu @, plus tacutii carora le iese aruncarea din `PARTEA_NEMENTIONATILOR`.
    Zarurile se arunca *inainte* de a intreba personajul, tocmai ca sa nu ajungem sa cerem o
    replica de la cineva care tocmai a spus ca n-are nimic de adaugat.

    Fara nicio mentiune nu e nimeni chemat, deci toate cinci ar putea scrie PAS si mesajul meu
    ar ramane fara niciun raspuns pe ecran. De aceea sortii scot atunci exact un vorbitor
    obligat: consiliul nu raspunde cu tacere totala, dar nici nu se aduna tot la orice mesaj,
    cum facea inainte de M8.

    `sansa` e injectata ca testele sa nu depinda de zaruri reale.
    """
    mentionati = gaseste_mentiuni(text, personaje)
    if not mentionati:
        return [_tras_la_sorti(list(personaje), sansa)]

    taciti = [id_personaj for id_personaj in personaje if id_personaj not in mentionati]
    sansa_tacutului = PARTEA_NEMENTIONATILOR / len(taciti) if taciti else 0.0

    return mentionati + [id_personaj for id_personaj in taciti if sansa() < sansa_tacutului]


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
