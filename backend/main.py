from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ai_client import trimite_mesaj
from personaje import incarca_personaje

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"
PERSONAJE = incarca_personaje()

# M3: un singur personaj raspunde, hardcodat. Orchestrarea intre toate cele 5 vine la M5.
PERSONAJ_ACTIV = "maestra"


class MesajIntrare(BaseModel):
    text: str


@app.get("/")
def pagina_chat():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")
    return {"status": "ok", "model_raspunde": bool(raspuns.strip())}


@app.post("/api/mesaje")
def trimite(mesaj: MesajIntrare):
    personaj = PERSONAJE[PERSONAJ_ACTIV]
    raspuns = trimite_mesaj(
        mesaj.text,
        sistem=personaj["systemPrompt"],
        temperatura=personaj["temperaturaRecomandata"],
    )
    return {
        "personaj": personaj["nume"],
        "avatar": personaj["avatar"],
        "culoare": personaj["culoare"],
        "text": raspuns,
    }
