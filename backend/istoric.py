import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "conversatie.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexiune = sqlite3.connect(DB_PATH)
    try:
        conexiune.execute(
            "CREATE TABLE IF NOT EXISTS mesaje (id INTEGER PRIMARY KEY AUTOINCREMENT, continut TEXT NOT NULL)"
        )
        conexiune.commit()
    finally:
        conexiune.close()


def salveaza_mesaj(mesaj: dict) -> None:
    conexiune = sqlite3.connect(DB_PATH)
    try:
        conexiune.execute("INSERT INTO mesaje (continut) VALUES (?)", (json.dumps(mesaj),))
        conexiune.commit()
    finally:
        conexiune.close()


def incarca_istoric() -> list[dict]:
    conexiune = sqlite3.connect(DB_PATH)
    try:
        randuri = conexiune.execute("SELECT continut FROM mesaje ORDER BY id ASC").fetchall()
    finally:
        conexiune.close()
    return [json.loads(rand[0]) for rand in randuri]
