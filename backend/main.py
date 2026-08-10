from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from ai_client import trimite_mesaj

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
def pagina_chat():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    raspuns = trimite_mesaj("Raspunde cu un singur cuvant: OK.")
    return {"status": "ok", "model_raspunde": bool(raspuns.strip())}
