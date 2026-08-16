import json
import re
from pathlib import Path

PERSONAJE_PATH = Path(__file__).parent.parent / "personaje.json"

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


def alege_destinatarii(text: str, personaje: dict) -> list[str]:
    """Cine raspunde: cei mentionati cu @, iar fara nicio mentiune - tot consiliul."""
    return gaseste_mentiuni(text, personaje) or list(personaje)
