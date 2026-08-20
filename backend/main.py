import json
import random
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

import istoric
import rezumat
from ai_client import (
    fara_pas,
    fara_replici_degenerate,
    preincarca,
    trimite_mesaj,
    trimite_mesaj_stream,
)
from personaje import (
    alege_vorbitorul,
    chemati_fara_raspuns,
    gaseste_mentiuni,
    incarca_personaje,
    obligati_sa_raspunda,
    profil_public,
    vorbitorii_rundei,
)

# Se adauga la system prompt-ul celor care nu pot sa taca: cei chemati pe nume si cei carora
# le-a iesit aruncarea. Restul isi pastreaza dreptul de a scrie PAS.
INDEMN_OBLIGAT = (
    "\n\nAcum e rândul tău și nu poți să taci: scrie o replică scurtă, nu PAS."
)

# Cate replici mai duce conversatia singura, dupa ce se termina runda pornita de mesajul meu.
# Numarul se trage la sorti intre plafoane, nu la infinit: pe gemma4:e2b, dupa vreo 8-10 replici
# autonome discutia intra in bucla si personajele incep sa se repete. Se opreste inainte de asta.
REPLICI_AUTONOME = (2, 4)

# Cat asteapta pagina intre doua replici autonome, in secunde. Singurul loc de unde se schimba
# intervalul: pagina il primeste in evenimentul `continua`, nu si-l alege singura. Slide-urile
# sesiunii 11 sugereaza 0-300s, dar cinci minute intre replici sunt absurde pentru o sedinta de
# 20 de minute - conversatia ar parea inghetata.
PAUZA_SECUNDE = (5, 20)

# Cate personaje se intreaba cel mult pentru o singura replica autonoma. Cine e ales poate tot
# sa scrie PAS, iar atunci replica nu se pierde: se incearca altcineva. Fara plafon, o discutie
# stinsa ar cere un apel la model pentru fiecare personaj, la fiecare replica.
INCERCARI_PE_REPLICA = 3

# Cat de lung poate fi un mesaj de-al meu. Nu e o precautie: peste vreo 20.000 de litere,
# Ollama scoate system prompt-ul din fereastra ca sa faca loc mesajului, iar ce raspunde nu
# mai e personajul, ci un asistent generic care nici nu stie de PAS (masurat pe gemma4:e2b,
# 20 august 2026, la 20.000 si la 100.000 de litere). 2000 e un paragraf lung de intrebare,
# mult peste orice s-a scris pana acum in consiliu. Aceeasi valoare e si `maxlength`-ul
# casetei din `static/index.html`, ca refuzul sa nu se vada niciodata din pagina.
LITERE_IN_MESAJ = 2000

# Tipurile de eveniment cu care se poate incheia o replica. Orice altceva inseamna ca runda s-a
# oprit la mijloc si nu mai are cine sa asculte urmarea.
SFARSITURI = ("gata", "tace", "eroare")

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


def numarul_rundei() -> int:
    """Runda in curs. Pagina il primeste in evenimentul `continua` si il da inapoi cand cere o
    replica autonoma, ca una ramasa dintr-o runda peste care am scris sa nu mai apuce sa vorbeasca."""
    return _runda_curenta


def cate_replici_autonome(sansa=random.random) -> int:
    """Cate replici mai are conversatia de dus singura, tras la sorti intre `REPLICI_AUTONOME`.

    `min` tine numarul sub plafon si daca un fals de test da chiar 1.0, ceea ce `random.random`
    nu da niciodata.
    """
    minim, maxim = REPLICI_AUTONOME
    return min(minim + int(sansa() * (maxim - minim + 1)), maxim)


def salveaza_replica(numar: int, id_conversatie: str, mesaj: dict) -> bool:
    """Replica intra in istoric doar daca runda ei mai e cea curenta si conversatia mai exista.

    A doua conditie e pentru conversatia stearsa cat vorbea consiliul: replicile ramase n-au
    unde se duce si nu trebuie sa refaca fisierul tocmai aruncat.
    """
    with _lacat_runde:
        if runda_anulata(numar):
            return False
        return istoric.salveaza_mesaj(id_conversatie, mesaj)


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
    text: str = Field(max_length=LITERE_IN_MESAJ)


class TitluIntrare(BaseModel):
    titlu: str


class ContinuareIntrare(BaseModel):
    # Numarul rundei din care vine replica: una ramasa dintr-o runda peste care am scris nu mai
    # are ce cauta pe ecran.
    runda: int


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
    """„E viu?" trebuie sa raspunda si cand modelul nu e: cu Ollama oprit, o eroare de server
    n-ar spune daca a picat serverul sau doar modelul din spatele lui."""
    try:
        raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")
    except Exception as eroare:
        return {"status": "ok", "model_raspunde": False, "detaliu": str(eroare)}
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


@app.get("/api/conversatii/{id_conversatie}/rezumat")
def memoria(id_conversatie: str):
    """Ce tine minte consiliul din partea de sedinta care nu mai incape in context.

    Pagina il cere la deschiderea conversatiei; in timpul unei runde il afla din evenimentul
    `rezumat`, fara sa mai intrebe.
    """
    conversatie = _conversatie_sau_404(id_conversatie)
    return {
        "rezumat": conversatie.get("rezumat", ""),
        "panaLa": conversatie.get("rezumatPanaLa", 0),
    }


def _context_dinaintea_mesajului_meu(context: list[dict], mesajul_meu: str) -> list[dict]:
    """Contextul taiat inainte de mesajul meu, cu tot ce a venit dupa el scos.

    Serveste doar celei de-a doua incercari: replicile de dupa mesajul meu sunt exact cele care
    l-au incurcat pe cel obligat. Daca mesajul meu nu mai e in fereastra, nu se taie nimic.
    """
    for pozitie in range(len(context) - 1, -1, -1):
        if context[pozitie]["content"] == mesajul_meu:
            return context[:pozitie]
    return context


async def replica_personajului(
    id_conversatie: str,
    personaj: dict,
    numar: int,
    cerere: Request,
    sistem: str,
    intrebare_implicita: str,
    obligat: bool = False,
):
    """Evenimentele unei singure replici, in ordinea in care ajung pe ecran.

    Ultimul spune cum s-a incheiat: `gata`, `tace` sau `eroare`. Daca runda s-a oprit la
    mijloc, generatorul se termina fara niciunul dintre ele - de-asta se yield-eaza dictionare,
    nu linii gata scrise: cine cheama vede si el ce s-a intamplat, fara sa desfaca JSON-ul.

    Cine e `obligat` are doua incercari, nu una. Prima merge dupa regula obisnuita, la ultima
    replica din chat; daca aceea era o intrebare si a iesit un raspuns de un cuvant, filtrele
    il inghit, iar cel convocat pe nume ar disparea cu totul - adica exact runda goala pe care
    a reparat-o M9. A doua incercare il intreaba mesajul meu, cel care l-a si convocat, cu
    replicile de dupa el scoase din context. Dupa ea nu se mai insista: tacerea se anunta.
    """
    yield {"tip": "personaj", **profil_public(personaj)}

    incercari = (False, True) if obligat else (False,)
    for a_doua in incercari:
        # Contextul se citeste abia acum, nu la inceputul rundei: asa fiecare aude ce s-a zis
        # inaintea lui. Ultimul mesaj din el e replica la care raspunde, deci iese din context
        # si intra ca intrebare curenta.
        context = istoric.context_pentru(id_conversatie, personaj["id"])
        if a_doua:
            context = _context_dinaintea_mesajului_meu(context, intrebare_implicita)
            intrebare = intrebare_implicita
        else:
            intrebare = context.pop()["content"] if context else intrebare_implicita

        text_complet = ""
        try:
            bucati = trimite_mesaj_stream(
                intrebare,
                personaj["nume"],
                sistem=sistem,
                temperatura=personaj["temperaturaRecomandata"],
                context=context,
            )
            # Asteptarea dupa model se muta pe alt fir: bucla de evenimente ramane libera sa
            # primeasca mesajul meu urmator, altfel "am prioritate" ar fi doar o vorba.
            # Cele doua filtre inghit si abtinerea, si replica degenerata, amandoua in stream,
            # deci un text gol aici inseamna "n-a avut ce spune", nu "a raspuns cu nimic".
            async for bucata in iterate_in_threadpool(fara_replici_degenerate(fara_pas(bucati))):
                if await trebuie_oprita(numar, cerere):
                    return
                text_complet += bucata
                yield {"tip": "text", "text": bucata}
        except Exception as eroare:
            # Pe ecran ajunge o bula rosie scurta, dar motivul trebuie sa ramana undeva: fara
            # el, „modelul nu a raspuns" nu spune daca a picat Ollama, daca a crapat incarcarea
            # pe GPU sau daca modelul nu e descarcat.
            print(f"[avertisment] {personaj['nume']} n-a primit raspuns de la model: {eroare}")
            yield {"tip": "eroare", "text": "modelul nu a raspuns"}
            return

        if text_complet.strip():
            break
        if a_doua or not obligat:
            yield {"tip": "tace"}
            return

    # Daca intre timp am scris peste runda, replica nu se salveaza: pagina a sters deja bula pe
    # jumatate scrisa, iar ce nu se vede n-are voie sa reapara la refresh.
    if not salveaza_replica(numar, id_conversatie, _mesaj_de_salvat(personaj, text_complet)):
        return

    yield {"tip": "gata"}


@app.post("/api/conversatii/{id_conversatie}/mesaje")
async def trimite(id_conversatie: str, mesaj: MesajIntrare, cerere: Request):
    _conversatie_sau_404(id_conversatie)
    # Nu mai e intrebat tot consiliul: se aleg cei care iau cuvantul, iar PAS ramane doar
    # pentru cine e ales fara sa fie si obligat (M15).
    vorbitori = vorbitorii_rundei(mesaj.text, PERSONAJE, sansa=zaruri)
    coada = list(vorbitori)
    obligati = set(obligati_sa_raspunda(mesaj.text, vorbitori, PERSONAJE, sansa=zaruri))
    numar = incepe_runda(id_conversatie, {**UTILIZATOR, "eu": True, "text": mesaj.text})
    # O data pe runda, nu la fiecare personaj: memoria se reface abia la capatul ei.
    memoria_in_prompt = rezumat.bloc_pentru_prompt(id_conversatie)

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

            # Memoria intra inaintea indemnului, ca INDEMN_OBLIGAT sa ramana ultimul lucru
            # pe care il citeste modelul - de asta atarna toata regula de la M10.
            sistem = personaj["systemPrompt"] + memoria_in_prompt
            if id_personaj in obligati:
                sistem += INDEMN_OBLIGAT

            text_complet = ""
            sfarsit = None
            async for eveniment in replica_personajului(
                id_conversatie, personaj, numar, cerere, sistem, mesaj.text, id_personaj in obligati
            ):
                if eveniment["tip"] == "text":
                    text_complet += eveniment["text"]
                sfarsit = eveniment["tip"]
                yield _eveniment(eveniment)

            if sfarsit not in SFARSITURI:
                return  # runda s-a oprit la mijlocul replicii
            if sfarsit != "gata":
                continue

            a_vorbit_cineva = True

            # Cine e chemat pe nume raspunde, chiar daca chemarea vine de la un personaj, nu de
            # la mine: trece in fata cozii si pierde dreptul de a tacea.
            for pas, chemat in enumerate(gaseste_mentiuni(text_complet, PERSONAJE)):
                if chemat in au_vorbit:
                    continue
                if chemat in coada:
                    coada.remove(chemat)
                coada.insert(pas, chemat)
                obligati.add(chemat)

        # Sortii obliga un vorbitor dintre cei alesi cand nu e nicio mentiune (M9), dar pe un mesaj fara continut
        # („Multumesc, notat.") si cel obligat tace uneori - masurat 15 din 25 pe gemma4:e2b, cu
        # sase formulari de INDEMN_OBLIGAT incercate. Atunci ecranul ar ramane neschimbat si nu
        # s-ar distinge de un server picat, asa ca runda goala se anunta.
        if not a_vorbit_cineva:
            yield _eveniment({"tip": "consiliul_tace"})
            return

        # Nu se promite nimic dupa o runda peste care am scris deja: nici memorie refacuta,
        # nici replici autonome.
        if await trebuie_oprita(numar, cerere):
            return

        # Memoria lunga se reface acum, la capatul rundei. Apelul cere 2-4s pe gemma4:e2b, deci
        # aici e singurul loc unde nu se simte: replica urmatoare oricum vine dupa o pauza de
        # secunde. Pe alt fir, ca bucla de evenimente sa ramana libera pentru mesajul meu -
        # altfel "am prioritate" ar cadea exact pe cele cateva secunde de rezumat.
        memoria_noua = await run_in_threadpool(rezumat.actualizeaza_rezumat, id_conversatie)
        if memoria_noua:
            yield _eveniment({"tip": "rezumat", "text": memoria_noua})

        # De aici incolo conversatia poate merge singura cateva replici: pagina afla cate si cat
        # sa astepte intre ele, apoi le cere una cate una.
        yield _eveniment(
            {
                "tip": "continua",
                "runda": numar,
                "replici": cate_replici_autonome(sansa=zaruri),
                "pauzaSecunde": list(PAUZA_SECUNDE),
            }
        )

    return StreamingResponse(runda(), media_type="application/x-ndjson")


@app.post("/api/conversatii/{id_conversatie}/continuare")
async def continua(id_conversatie: str, date: ContinuareIntrare, cerere: Request):
    """O singura replica pe care conversatia si-o da singura, fara ca eu sa fi scris ceva.

    Vorbeste unul singur, ales dupa regula 80/20 - spre deosebire de runda pornita de mesajul
    meu, unde e intrebat fiecare. Pauza dintre replici o tine pagina: doar ea stie daca am
    inceput sa scriu, iar cat am text in caseta nimeni nu vorbeste.
    """
    _conversatie_sau_404(id_conversatie)
    numar = date.runda

    async def replica_de_la_sine():
        # Aceeasi fereastra ca a contextului: o chemare mai veche decat ce mai tine minte
        # consiliul n-are cum sa astepte la nesfarsit un raspuns.
        mesaje = istoric.incarca_istoric(id_conversatie)[-istoric.MESAJE_IN_CONTEXT :]
        if not mesaje:
            return

        chemati = chemati_fara_raspuns(mesaje, PERSONAJE)
        # Cine tocmai a vorbit nu incepe si replica urmatoare. Pe masura ce se incearca, ies din
        # joc si cei care au tacut: replica se da altcuiva, nu se cere de doua ori de la acelasi.
        exclusi = [mesaje[-1]["personajId"]] if not mesaje[-1].get("eu") else []

        for _ in range(INCERCARI_PE_REPLICA):
            if await trebuie_oprita(numar, cerere):
                return

            id_personaj = alege_vorbitorul(PERSONAJE, chemati, exclusi, sansa=zaruri)
            if id_personaj is None:
                return
            exclusi.append(id_personaj)
            personaj = PERSONAJE[id_personaj]

            sfarsit = None
            # Fara INDEMN_OBLIGAT: nimeni nu l-a chemat pe nume, deci are voie sa scrie PAS.
            sistem = personaj["systemPrompt"] + rezumat.bloc_pentru_prompt(id_conversatie)
            async for eveniment in replica_personajului(
                id_conversatie, personaj, numar, cerere, sistem, mesaje[-1]["text"]
            ):
                sfarsit = eveniment["tip"]
                yield _eveniment(eveniment)

            if sfarsit != "tace":
                return

    return StreamingResponse(replica_de_la_sine(), media_type="application/x-ndjson")
