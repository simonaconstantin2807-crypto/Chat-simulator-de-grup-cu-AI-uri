import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

import istoric
from ai_client import preincarca, trimite_mesaj, trimite_mesaj_stream
from personaje import incarca_personaje


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
istoric.init_db()

# M3: un singur personaj raspunde, hardcodat. Orchestrarea intre toate cele 5 vine la M5.
PERSONAJ_ACTIV = "maestra"

# Fara cont/login (SPEC.md) - o singura utilizatoare hardcodata.
UTILIZATOR = {"nume": "Simona", "avatar": "🙋", "culoare": "#6c5ce7"}


class MesajIntrare(BaseModel):
    text: str


@app.get("/")
def pagina_chat():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")
    return {"status": "ok", "model_raspunde": bool(raspuns.strip())}


@app.get("/api/mesaje")
def istoricul():
    return istoric.incarca_istoric()


@app.post("/api/mesaje")
def trimite(mesaj: MesajIntrare):
    personaj = PERSONAJE[PERSONAJ_ACTIV]
    istoric.salveaza_mesaj({**UTILIZATOR, "eu": True, "text": mesaj.text})

    def raspuns_stream():
        metadate = {"nume": personaj["nume"], "avatar": personaj["avatar"], "culoare": personaj["culoare"]}
        yield json.dumps(metadate) + "\n"

        text_complet = ""
        try:
            for bucata in trimite_mesaj_stream(
                mesaj.text,
                personaj["nume"],
                sistem=personaj["systemPrompt"],
                temperatura=personaj["temperaturaRecomandata"],
            ):
                text_complet += bucata
                yield bucata
        except Exception:
            yield "\n[eroare: modelul nu a raspuns]"
            return

        istoric.salveaza_mesaj({**metadate, "eu": False, "text": text_complet})

    return StreamingResponse(raspuns_stream(), media_type="text/plain")
