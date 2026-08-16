import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import istoric
from ai_client import preincarca, trimite_mesaj, trimite_mesaj_stream
from personaje import alege_destinatarii, incarca_personaje, profil_public


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


@app.get("/api/mesaje")
def istoricul():
    return istoric.incarca_istoric()


@app.post("/api/mesaje")
def trimite(mesaj: MesajIntrare):
    destinatari = alege_destinatarii(mesaj.text, PERSONAJE)

    # Contextul se citeste inainte de prima replica: toti intra in runda cu acelasi istoric,
    # deci nimeni nu aude ce a raspuns altcineva intre timp.
    contexte = {id_personaj: istoric.context_pentru(id_personaj) for id_personaj in destinatari}
    istoric.salveaza_mesaj({**UTILIZATOR, "eu": True, "text": mesaj.text})

    def runda():
        for id_personaj in destinatari:
            personaj = PERSONAJE[id_personaj]
            yield _eveniment({"tip": "personaj", **profil_public(personaj)})

            text_complet = ""
            try:
                for bucata in trimite_mesaj_stream(
                    mesaj.text,
                    personaj["nume"],
                    sistem=personaj["systemPrompt"],
                    temperatura=personaj["temperaturaRecomandata"],
                    context=contexte[id_personaj],
                ):
                    text_complet += bucata
                    yield _eveniment({"tip": "text", "text": bucata})
            except Exception:
                yield _eveniment({"tip": "eroare", "text": "modelul nu a raspuns"})
                continue

            istoric.salveaza_mesaj(_mesaj_de_salvat(personaj, text_complet))
            yield _eveniment({"tip": "gata"})

    return StreamingResponse(runda(), media_type="application/x-ndjson")
