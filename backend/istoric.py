"""Memoria conversatiilor: cate un fisier JSON local pentru fiecare, rescris la fiecare mesaj.

Fisierele supravietuiesc restartarii serverului, iar la deschiderea unei conversatii pagina
citeste intreg fisierul ei. JSON si nu o baza de date, pentru ca o sedinta de consiliu are zeci
de mesaje, nu milioane, si e util sa poti deschide `data/conversatii/<id>.json` ca sa vezi ce a
primit modelul.

Fisierul isi tine si titlul, nu doar mesajele, iar lista de conversatii se obtine citind
folderul. Un index separat ar fi fost mai rapid, dar ar fi insemnat doua surse de adevar care se
pot desincroniza - la cateva zeci de sedinte, citirea folderului nu se simte.
"""

import json
import re
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

DATE_DIR = Path(__file__).parent / "data"

# Conversatia unica de dinainte de conversatiile multiple. E migrata la prima pornire care o
# gaseste si de atunci nu mai e citita niciodata.
NUME_ISTORIC_VECHI = "conversatie.json"

# Cate mesaje din istoric primeste un personaj in prompt. Cu cat contextul e mai lung, cu atat
# primul token intarzie mai mult pe un model local. Erau 12 cat timp un personaj isi vedea doar
# propriile replici - o runda insemna 2 mesaje. De cand se aud intre ele, o runda de consiliu
# intreg inseamna 6, deci 12 ar fi acoperit doua runde: prea putin ca sa poata comenta ceva zis
# mai devreme. 24 tin vreo patru runde. Creste odata cu numarul de personaje. Conversatiile
# separate nu schimba fereastra: fiecare are istoricul ei, deci si fereastra ei.
MESAJE_IN_CONTEXT = 24

# Cat se ia din primul meu mesaj ca sa iasa titlul. Sase cuvinte prind intrebarea („Merită să
# simulăm AB-ul pe…"), iar plafonul de caractere taie mesajele scrise dintr-o rasuflare, fara
# spatii de care sa se agate numaratoarea de cuvinte.
CUVINTE_IN_TITLU = 6
LITERE_IN_TITLU = 26

# Ce nu iese in lista de conversatii. Lista se cere la fiecare mesaj trimis, ca titlul si ordinea
# sa fie proaspete, deci e un cuprins: nici arhiva, nici memoria fiecarei sedinte.
CAMPURI_ASCUNSE_IN_LISTA = ("mesaje", "rezumat", "rezumatPanaLa")

# Id-ul vine din URL si devine nume de fisier, deci se accepta doar ce nu poate iesi din folder.
TIPAR_ID = re.compile(r"^[A-Za-z0-9_-]+$")

# Endpoint-urile FastAPI sincrone ruleaza pe fire diferite, iar salvarea e citeste-si-rescrie.
_lacat = threading.Lock()


def _dir_conversatii() -> Path:
    return DATE_DIR / "conversatii"


def _cale(id_conversatie: str) -> Path | None:
    if not isinstance(id_conversatie, str) or not TIPAR_ID.match(id_conversatie):
        return None
    return _dir_conversatii() / f"{id_conversatie}.json"


def _acum() -> str:
    """Momentul, pana la microsecunda: pe secunda intreaga, doua conversatii atinse in aceeasi
    secunda ies la egalitate si lista nu mai stie care e cea folosita ultima."""
    return datetime.now().isoformat()


def _scrie(conversatie: dict) -> None:
    cale = _cale(conversatie["id"])
    cale.parent.mkdir(parents=True, exist_ok=True)
    cale.write_text(json.dumps(conversatie, ensure_ascii=False, indent=2), encoding="utf-8")


def titlu_din_mesaj(text: str) -> str:
    """Primele cuvinte din mesaj, ca sa nu fiu obligata sa scriu eu titlul fiecarei sedinte."""
    cuvinte = text.split()
    titlu = " ".join(cuvinte[:CUVINTE_IN_TITLU])
    taiat = len(cuvinte) > CUVINTE_IN_TITLU

    if len(titlu) > LITERE_IN_TITLU:
        titlu = titlu[:LITERE_IN_TITLU].rstrip()
        taiat = True

    return f"{titlu}…" if taiat and titlu else titlu


def _id_nou() -> str:
    """Id lizibil, cu data in fata: se vede din numele fisierului cand a inceput sedinta.

    Sufixul aleator tine id-ul unic si cand sterg o conversatie si fac alta in aceeasi secunda -
    altfel cea noua i-ar mosteni numele, iar conversatia tinuta minte de pagina ar fi alta decat
    cea de dinainte de refresh.
    """
    baza = datetime.now().strftime("conv-%Y%m%d-%H%M%S")
    id_conversatie = f"{baza}-{uuid4().hex[:4]}"
    while _cale(id_conversatie).exists():
        id_conversatie = f"{baza}-{uuid4().hex[:4]}"
    return id_conversatie


def creeaza_conversatie(titlu: str = "", mesaje: list[dict] | None = None) -> dict:
    """O conversatie noua. Titlul gol inseamna „inca nenumita" - il pune primul meu mesaj."""
    with _lacat:
        conversatie = {
            "id": _id_nou(),
            "titlu": titlu,
            "creatLa": _acum(),
            "actualizatLa": _acum(),
            "mesaje": mesaje or [],
        }
        _scrie(conversatie)
        return conversatie


def citeste_conversatie(id_conversatie: str) -> dict | None:
    cale = _cale(id_conversatie)
    if cale is None or not cale.exists():
        return None
    continut = cale.read_text(encoding="utf-8").strip()
    return json.loads(continut) if continut else None


def _cuprins(conversatie: dict) -> dict:
    """Un rand din lista: tot despre conversatie, mai putin mesajele si rezumatul ei.

    Lista se cere la fiecare mesaj trimis, ca titlul si ordinea sa fie proaspete; daca ar cara
    si arhiva dupa ea, ar trimite in pagina toata discutia de fiecare data.
    """
    return {
        **{
            camp: valoare
            for camp, valoare in conversatie.items()
            if camp not in CAMPURI_ASCUNSE_IN_LISTA
        },
        "numarMesaje": len(conversatie.get("mesaje", [])),
    }


def listeaza_conversatii() -> list[dict]:
    """Cuprinsul, fara mesaje: cea folosita ultima e prima, ca intr-o aplicatie de chat."""
    cuprins = []
    for cale in _dir_conversatii().glob("*.json"):
        conversatie = citeste_conversatie(cale.stem)
        if conversatie:
            cuprins.append(_cuprins(conversatie))

    return sorted(cuprins, key=lambda c: (c["actualizatLa"], c["id"]), reverse=True)


def incarca_istoric(id_conversatie: str) -> list[dict]:
    conversatie = citeste_conversatie(id_conversatie)
    return conversatie["mesaje"] if conversatie else []


def salveaza_mesaj(id_conversatie: str, mesaj: dict) -> None:
    with _lacat:
        conversatie = citeste_conversatie(id_conversatie)
        if not conversatie:
            return

        conversatie["mesaje"].append(mesaj)
        conversatie["actualizatLa"] = _acum()
        # Titlul se pune o singura data, din primul mesaj al meu: replicile personajelor n-au
        # cum sa spuna despre ce e sedinta, iar un titlu scris de mine e o decizie, nu o
        # valoare provizorie peste care se poate trece.
        if not conversatie["titlu"] and mesaj.get("eu"):
            conversatie["titlu"] = titlu_din_mesaj(mesaj.get("text", ""))

        _scrie(conversatie)


def rezumatul(id_conversatie: str) -> tuple[str, int]:
    """Memoria lunga a conversatiei: textul si cate mesaje sunt deja stranse in el.

    Al doilea numar tine actualizarea incrementala: de la el incolo incepe ce inca n-a fost
    rezumat. Conversatiile scrise inainte de memoria lunga n-au niciunul din cele doua campuri,
    deci pornesc de la zero fara migrare.
    """
    conversatie = citeste_conversatie(id_conversatie) or {}
    return conversatie.get("rezumat", ""), conversatie.get("rezumatPanaLa", 0)


def salveaza_rezumat(id_conversatie: str, text: str, pana_la: int) -> None:
    """Scrie memoria in fisierul conversatiei, ca sa supravietuiasca restartului ca si mesajele.

    Nu atinge `actualizatLa`: ordinea din lista o dau mesajele mele, iar rezumatul se reface in
    fundal - o conversatie n-are de ce sa sara in capul listei fara ca eu sa fi scris in ea.
    """
    with _lacat:
        conversatie = citeste_conversatie(id_conversatie)
        if not conversatie:
            return

        conversatie["rezumat"] = text
        conversatie["rezumatPanaLa"] = pana_la
        _scrie(conversatie)


def redenumeste_conversatie(id_conversatie: str, titlu: str) -> dict | None:
    with _lacat:
        conversatie = citeste_conversatie(id_conversatie)
        if not conversatie:
            return None

        conversatie["titlu"] = titlu.strip()
        _scrie(conversatie)
        return _cuprins(conversatie)


def sterge_conversatie(id_conversatie: str) -> bool:
    with _lacat:
        cale = _cale(id_conversatie)
        if cale is None or not cale.exists():
            return False
        cale.unlink()
        return True


def asigura_o_conversatie() -> dict:
    """Exista mereu macar o conversatie: altfel n-as avea unde scrie dupa ce le sterg pe toate."""
    existente = listeaza_conversatii()
    return existente[0] if existente else creeaza_conversatie()


def _migreaza_conversatia_unica() -> None:
    """Discutia dinainte de conversatiile multiple devine prima conversatie din lista.

    Fisierul vechi e redenumit dupa migrare, nu sters: daca ceva iese prost, discutia e tot
    acolo, iar `conversatie.json` care nu mai exista e si semnalul ca migrarea s-a facut deja.
    """
    vechi = DATE_DIR / NUME_ISTORIC_VECHI
    if not vechi.exists():
        return

    continut = vechi.read_text(encoding="utf-8").strip()
    mesaje = json.loads(continut) if continut else []
    primul_meu = next((m for m in mesaje if m.get("eu")), None)
    creeaza_conversatie(titlu_din_mesaj(primul_meu["text"]) if primul_meu else "", mesaje)

    vechi.rename(vechi.with_suffix(".json.migrat"))


def init_stocare() -> None:
    _dir_conversatii().mkdir(parents=True, exist_ok=True)
    _migreaza_conversatia_unica()
    asigura_o_conversatie()


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


def context_pentru(
    id_conversatie: str, personaj_id: str, limita: int = MESAJE_IN_CONTEXT
) -> list[dict]:
    """Ultimele mesaje pe care le primeste personajul in prompt, in formatul de chat al modelului.

    Vede toata discutia din conversatia curenta - si numai din ea: ce am scris eu, ce a raspuns
    el si ce au zis ceilalti, altfel regula "cele mai bune momente sunt cand contrazici pe
    altcineva" din system prompt-uri n-are cum sa fie dusa la capat. Ce s-a discutat in alta
    conversatie nu ajunge aici: doua sedinte de consiliu diferite nu se aud una pe alta.

    Ce a iesit din fereastra nu se pierde, dar nu trece pe aici: memoria lunga intra in system
    prompt, prin `rezumat.bloc_pentru_prompt`. Motivul e masurat, e scris acolo.
    """
    return [_replica(mesaj, personaj_id) for mesaj in incarca_istoric(id_conversatie)[-limita:]]
