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
# primul token intarzie mai mult pe un model local. Erau 12 cat timp un personaj isi vedea doar
# propriile replici - o runda insemna 2 mesaje. De cand se aud intre ele, o runda de consiliu
# intreg inseamna 6, deci 12 ar fi acoperit doua runde: prea putin ca sa poata comenta ceva zis
# mai devreme. 24 tin vreo patru runde. Creste odata cu numarul de personaje.
MESAJE_IN_CONTEXT = 24

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


def _replica(mesaj: dict, personaj_id: str) -> dict:
    """Un mesaj din istoric, vazut cu ochii personajului dat.

    Modelul cunoaste doua roluri: `assistant` e propria lui voce, `user` e tot restul. Ce a
    zis altcineva intra deci ca `user`, dar cu numele in fata - fara el, vocea mea si a
    celorlalte personaje s-ar topi intr-una singura si n-ar sti cui raspunde. Propriile
    replici raman curate: prefixul l-ar invata sa-si semneze mesajele.
    """
    if mesaj.get("personajId") == personaj_id:
        return {"role": "assistant", "content": mesaj["text"]}
    if mesaj.get("eu"):
        return {"role": "user", "content": mesaj["text"]}

    vorbitor = mesaj.get("nume") or mesaj.get("personajId", "Cineva")
    return {"role": "user", "content": f"{vorbitor}: {mesaj['text']}"}


def context_pentru(personaj_id: str, limita: int = MESAJE_IN_CONTEXT) -> list[dict]:
    """Ultimele mesaje pe care le primeste personajul in prompt, in formatul de chat al modelului.

    Vede toata discutia: ce am scris eu, ce a raspuns el si ce au zis ceilalti - altfel
    regula "cele mai bune momente sunt cand contrazici pe altcineva" din system prompt-uri
    n-are cum sa fie dusa la capat.
    """
    return [_replica(mesaj, personaj_id) for mesaj in incarca_istoric()[-limita:]]
