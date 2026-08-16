"""Memoria conversatiei: un singur fisier JSON local, rescris la fiecare mesaj nou.

Fisierul supravietuieste restartarii serverului, iar la pornire pagina il citeste intreg.
JSON si nu o baza de date, pentru ca o sedinta de consiliu are zeci de mesaje, nu milioane,
si e util sa poti deschide `data/conversatie.json` ca sa vezi ce a primit modelul.
"""

import json
import threading
from pathlib import Path

ISTORIC_PATH = Path(__file__).parent / "data" / "conversatie.json"

# Cate mesaje din istoric primeste un personaj in prompt. Cu cat contextul e mai lung, cu atat
# primul token intarzie mai mult pe un model local - 12 mesaje tin firul discutiei fara sa
# umfle promptul la fiecare runda.
MESAJE_IN_CONTEXT = 12

# Endpoint-urile FastAPI sincrone ruleaza pe fire diferite, iar salvarea e citeste-si-rescrie.
_lacat = threading.Lock()


def init_stocare() -> None:
    ISTORIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ISTORIC_PATH.exists():
        ISTORIC_PATH.write_text("[]", encoding="utf-8")


def incarca_istoric() -> list[dict]:
    if not ISTORIC_PATH.exists():
        return []
    continut = ISTORIC_PATH.read_text(encoding="utf-8").strip()
    return json.loads(continut) if continut else []


def salveaza_mesaj(mesaj: dict) -> None:
    with _lacat:
        mesaje = incarca_istoric()
        mesaje.append(mesaj)
        ISTORIC_PATH.parent.mkdir(parents=True, exist_ok=True)
        ISTORIC_PATH.write_text(
            json.dumps(mesaje, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def context_pentru(personaj_id: str, limita: int = MESAJE_IN_CONTEXT) -> list[dict]:
    """Ultimele mesaje pe care le primeste personajul in prompt, in formatul de chat al modelului.

    Vede ce am scris eu si ce a raspuns el insusi mai devreme - nu si replicile celorlalte
    personaje. Ca personajele sa se auda intre ele e nevoie si de o logica de tura (cine
    vorbeste si cand), asa ca ramane pe etapa urmatoare; aici se schimba doar filtrul.
    """
    relevante = [
        mesaj
        for mesaj in incarca_istoric()
        if mesaj.get("eu") or mesaj.get("personajId") == personaj_id
    ]
    return [
        {"role": "user" if mesaj.get("eu") else "assistant", "content": mesaj["text"]}
        for mesaj in relevante[-limita:]
    ]
