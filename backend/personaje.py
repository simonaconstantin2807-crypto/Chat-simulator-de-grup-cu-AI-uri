import json
from pathlib import Path

PERSONAJE_PATH = Path(__file__).parent.parent / "personaje.json"


def incarca_personaje() -> dict:
    date = json.loads(PERSONAJE_PATH.read_text(encoding="utf-8"))
    return {p["id"]: p for p in date["personaje"]}
