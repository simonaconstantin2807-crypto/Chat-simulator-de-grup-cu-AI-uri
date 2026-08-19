import json
import random
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool

import istoric
from ai_client import fara_pas, preincarca, trimite_mesaj, trimite_mesaj_stream
from personaje import (
    gaseste_mentiuni,
    incarca_personaje,
    obligati_sa_raspunda,
    ordinea_vorbitorilor,
    profil_public,
)

# Se adauga la system prompt-ul celor care nu pot sa taca: cei chemati pe nume si cei carora
# le-a iesit aruncarea. Restul isi pastreaza dreptul de a scrie PAS.
INDEMN_OBLIGAT = (
    "\n\nAcum e rândul tău și nu poți să taci: scrie o replică scurtă, nu PAS."
)

# Aruncarea cu banul pentru cei nementionati, scoasa la nivel de modul ca testele s-o poata fixa.
zaruri = random.random

# Numarul rundei in curs. Am prioritate fata de consiliu (M9): mesajul meu nou incepe o runda
# noua, iar cea veche se opreste cand vede ca numarul ei nu mai e cel curent. Fara asta, doua
# runde ar scrie in acelasi ecran si in acelasi istoric. Numarul e unul singur peste toate
# conversatiile: e o singura utilizatoare, cu o singura fereastra in fata - o runda lasata in
# urma intr-o alta conversatie n-are cui sa mai scrie.
_runda_curenta = 0

# Acelasi lacat numeroteaza rundele si scrie in istoric, ca o runda tocmai anulata sa nu apuce
# sa strecoare o replica dupa mesajul care a anulat-o.
_lacat_runde = threading.Lock()


def incepe_runda(id_conversatie: str, mesaj_utilizator: dict) -> int:
    """Salveaza mesajul meu si intoarce numarul rundei noi. De aici, cea veche e anulata."""
    global _runda_curenta
    with _lacat_runde:
        _runda_curenta += 1
        istoric.salveaza_mesaj(id_conversatie, mesaj_utilizator)
        return _runda_curenta


def runda_anulata(numar: int) -> bool:
    return numar != _runda_curenta


def salveaza_replica(numar: int, id_conversatie: str, mesaj: dict) -> bool:
    """Replica intra in istoric doar daca runda ei mai e cea curenta."""
    with _lacat_runde:
        if runda_anulata(numar):
            return False
        istoric.salveaza_mesaj(id_conversatie, mesaj)
        return True


async def trebuie_oprita(numar: int, cerere: Request) -> bool:
    """Runda si-a pierdut rostul: ori am scris peste ea, ori pagina nu mai asculta.

    A doua verificare tine de tokeni: fara ea, un tab inchis ar lasa modelul sa scrie pana la
    capat o runda pe care n-o mai vede nimeni.
    """
    return runda_anulata(numar) or await cerere.is_disconnected()


def incalzeste_modelul() -> None:
    try:
        preincarca()
    except Exception as eroare:
        # Daca Ollama nu e pornit, eroarea reapare oricum la primul mesaj, unde se si vede.
        print(f"[avertisment] preincarcarea modelului a esuat: {eroare}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In fundal, ca serverul sa raspunda imediat; modelul se incarca in paralel cu deschiderea paginii.
    threading.Thread(target=incalzeste_modelul, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"
PERSONAJE = incarca_personaje()
istoric.init_stocare()

# Fara cont/login (SPEC.md) - o singura utilizatoare hardcodata.
UTILIZATOR = {
    "id": "eu",
    "nume": "Simona",
    "rol": "Moderatoarea consiliului",
    "avatar": "🙋",
    "culoare": "#3D3A36",
    "culoareFundal": "#3D3A36",
}


class MesajIntrare(BaseModel):
    text: str


class TitluIntrare(BaseModel):
    titlu: str


def _conversatie_sau_404(id_conversatie: str) -> dict:
    conversatie = istoric.citeste_conversatie(id_conversatie)
    if not conversatie:
        raise HTTPException(status_code=404, detail="conversatia nu exista")
    return conversatie


def _eveniment(date: dict) -> str:
    """O linie NDJSON din fluxul de raspuns: pagina citeste linie cu linie, cat ii vine."""
    return json.dumps(date, ensure_ascii=False) + "\n"


def _mesaj_de_salvat(personaj: dict, text: str) -> dict:
    return {
        "eu": False,
        "personajId": personaj["id"],
        "nume": personaj["nume"],
        "avatar": personaj["avatar"],
        "culoare": personaj["culoare"],
        "culoareFundal": personaj["culoareFundal"],
        "text": text,
    }


@app.get("/")
def pagina_chat():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")
    return {"status": "ok", "model_raspunde": bool(raspuns.strip())}


@app.get("/api/personaje")
def profilurile():
    return {
        "utilizator": UTILIZATOR,
        "personaje": [profil_public(personaj) for personaj in PERSONAJE.values()],
    }


@app.get("/api/conversatii")
def conversatiile():
    return istoric.listeaza_conversatii()


@app.post("/api/conversatii")
def conversatie_noua():
    return istoric.creeaza_conversatie()


@app.patch("/api/conversatii/{id_conversatie}")
def redenumeste(id_conversatie: str, date: TitluIntrare):
    _conversatie_sau_404(id_conversatie)
    return istoric.redenumeste_conversatie(id_conversatie, date.titlu)


@app.delete("/api/conversatii/{id_conversatie}")
def sterge(id_conversatie: str):
    _conversatie_sau_404(id_conversatie)
    istoric.sterge_conversatie(id_conversatie)
    # Sterse toate, ramane una goala: pagina trebuie sa aiba mereu unde sa ma lase sa scriu.
    istoric.asigura_o_conversatie()
    return istoric.listeaza_conversatii()


@app.get("/api/conversatii/{id_conversatie}/mesaje")
def istoricul(id_conversatie: str):
    return _conversatie_sau_404(id_conversatie)["mesaje"]


@app.post("/api/conversatii/{id_conversatie}/mesaje")
async def trimite(id_conversatie: str, mesaj: MesajIntrare, cerere: Request):
    _conversatie_sau_404(id_conversatie)
    coada = ordinea_vorbitorilor(mesaj.text, PERSONAJE)
    obligati = set(obligati_sa_raspunda(mesaj.text, PERSONAJE, sansa=zaruri))
    numar = incepe_runda(id_conversatie, {**UTILIZATOR, "eu": True, "text": mesaj.text})

    async def runda():
        au_vorbit = set()
        a_vorbit_cineva = False

        while coada:
            if await trebuie_oprita(numar, cerere):
                return

            id_personaj = coada.pop(0)
            if id_personaj in au_vorbit:
                continue
            au_vorbit.add(id_personaj)
            personaj = PERSONAJE[id_personaj]

            # Contextul se citeste abia acum, nu la inceputul rundei: asa fiecare aude ce s-a
            # zis inaintea lui. Ultimul mesaj din el e replica la care raspunde, deci iese din
            # context si intra ca intrebare curenta.
            context = istoric.context_pentru(id_conversatie, id_personaj)
            intrebare = context.pop()["content"] if context else mesaj.text

            yield _eveniment({"tip": "personaj", **profil_public(personaj)})

            sistem = personaj["systemPrompt"]
            if id_personaj in obligati:
                sistem += INDEMN_OBLIGAT

            text_complet = ""
            try:
                bucati = trimite_mesaj_stream(
                    intrebare,
                    personaj["nume"],
                    sistem=sistem,
                    temperatura=personaj["temperaturaRecomandata"],
                    context=context,
                )
                # Asteptarea dupa model se muta pe alt fir: bucla de evenimente ramane libera
                # sa primeasca mesajul meu urmator, altfel "am prioritate" ar fi doar o vorba.
                # `fara_pas` inghite raspunsul celui care n-are nimic de adaugat, deci un text
                # gol aici inseamna "a ales sa taca", nu "a raspuns cu nimic".
                async for bucata in iterate_in_threadpool(fara_pas(bucati)):
                    if await trebuie_oprita(numar, cerere):
                        return
                    text_complet += bucata
                    yield _eveniment({"tip": "text", "text": bucata})
            except Exception:
                yield _eveniment({"tip": "eroare", "text": "modelul nu a raspuns"})
                continue

            if not text_complet.strip():
                yield _eveniment({"tip": "tace"})
                continue

            # Daca intre timp am scris peste runda, replica nu se salveaza: pagina a sters deja
            # bula pe jumatate scrisa, iar ce nu se vede n-are voie sa reapara la refresh.
            replica = _mesaj_de_salvat(personaj, text_complet)
            if not salveaza_replica(numar, id_conversatie, replica):
                return
            a_vorbit_cineva = True
            yield _eveniment({"tip": "gata"})

            # Cine e chemat pe nume raspunde, chiar daca chemarea vine de la un personaj, nu de
            # la mine: trece in fata cozii si pierde dreptul de a tacea.
            for pas, chemat in enumerate(gaseste_mentiuni(text_complet, PERSONAJE)):
                if chemat in au_vorbit:
                    continue
                if chemat in coada:
                    coada.remove(chemat)
                coada.insert(pas, chemat)
                obligati.add(chemat)

        # Sortii obliga un vorbitor cand nu e nicio mentiune (M9), dar pe un mesaj fara continut
        # („Multumesc, notat.") si cel obligat tace uneori - masurat 15 din 25 pe gemma4:e2b, cu
        # sase formulari de INDEMN_OBLIGAT incercate. Atunci ecranul ar ramane neschimbat si nu
        # s-ar distinge de un server picat, asa ca runda goala se anunta.
        if not a_vorbit_cineva:
            yield _eveniment({"tip": "consiliul_tace"})

    return StreamingResponse(runda(), media_type="application/x-ndjson")
