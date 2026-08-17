import json
import random
import re
from pathlib import Path

PERSONAJE_PATH = Path(__file__).parent.parent / "personaje.json"

# Cat din runda le ramane celor care n-au fost chemati pe nume. Cei mentionati raspund oricum,
# asa ca procentul asta nu se imparte cu ei: e sansa ca cineva sa intervina neinvitat. Se
# imparte egal la cati taciti sunt, deci ramane 20% si daca maine consiliul are noua membri.
PARTEA_NEMENTIONATILOR = 0.2

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


def probabilitati(text: str, personaje: dict) -> dict[str, float]:
    """Sansa fiecarui personaj de a intra in runda, dupa mentiunile din text.

    Cine e chemat pe nume raspunde sigur (1.0). Restul isi impart `PARTEA_NEMENTIONATILOR`.
    Fara nicio mentiune nu exista grup chemat, deci se convoaca tot consiliul (SPEC.md §3).
    """
    mentionati = set(gaseste_mentiuni(text, personaje))
    if not mentionati:
        return {id_personaj: 1.0 for id_personaj in personaje}

    taciti = [id_personaj for id_personaj in personaje if id_personaj not in mentionati]
    sansa_tacutului = PARTEA_NEMENTIONATILOR / len(taciti) if taciti else 0.0

    return {
        id_personaj: 1.0 if id_personaj in mentionati else sansa_tacutului
        for id_personaj in personaje
    }


def alege_destinatarii(text: str, personaje: dict, sansa=random.random) -> list[str]:
    """Cine raspunde efectiv: cei chemati, plus tacutii carora le-a iesit aruncarea.

    `sansa` e injectata ca testele sa nu depinda de zaruri reale.
    """
    mentionati = gaseste_mentiuni(text, personaje)
    if not mentionati:
        return list(personaje)

    sanse = probabilitati(text, personaje)
    intrusi = [
        id_personaj
        for id_personaj in personaje
        if id_personaj not in mentionati and sansa() < sanse[id_personaj]
    ]
    return mentionati + intrusi
