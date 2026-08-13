import json

from fastapi.testclient import TestClient

import istoric
from main import app

client = TestClient(app)


def _db_izolat(monkeypatch, tmp_path):
    monkeypatch.setattr(istoric, "DB_PATH", tmp_path / "test.db")
    istoric.init_db()


def test_pagina_chat_se_incarca():
    raspuns = client.get("/")

    assert raspuns.status_code == 200
    assert "text/html" in raspuns.headers["content-type"]


def test_health_confirma_modelul():
    raspuns = client.get("/api/health")

    assert raspuns.status_code == 200
    corp = raspuns.json()
    assert corp["status"] == "ok"
    assert corp["model_raspunde"] is True


def test_trimite_mesaj_streameaza_raspunsul_maestrei(monkeypatch, tmp_path):
    _db_izolat(monkeypatch, tmp_path)

    with client.stream(
        "POST", "/api/mesaje", json={"text": "Ce parere ai despre AB simulat pe poza?"}
    ) as raspuns:
        assert raspuns.status_code == 200
        linii = list(raspuns.iter_lines())

    metadate = json.loads(linii[0])
    text = "".join(linii[1:])

    assert metadate["nume"] == "Maestra"
    assert "avatar" in metadate and "culoare" in metadate
    assert text.strip() != ""


def test_trimite_mesaj_persista_mesajul_utilizatoarei_si_al_personajului(monkeypatch, tmp_path):
    _db_izolat(monkeypatch, tmp_path)

    with client.stream("POST", "/api/mesaje", json={"text": "Salut, consiliu!"}) as raspuns:
        list(raspuns.iter_lines())

    istoricul = client.get("/api/mesaje").json()

    assert any(m["eu"] and m["text"] == "Salut, consiliu!" for m in istoricul)
    assert any(not m["eu"] and m["nume"] == "Maestra" and m["text"].strip() != "" for m in istoricul)


def test_istoric_gol_la_start(monkeypatch, tmp_path):
    _db_izolat(monkeypatch, tmp_path)

    raspuns = client.get("/api/mesaje")

    assert raspuns.status_code == 200
    assert raspuns.json() == []


def test_istoric_intoarce_mesajele_salvate_in_ordine(monkeypatch, tmp_path):
    _db_izolat(monkeypatch, tmp_path)
    mesaj1 = {"eu": True, "nume": "Simona", "avatar": "🙋", "culoare": "#6c5ce7", "text": "Salut"}
    mesaj2 = {"eu": False, "nume": "Maestra", "avatar": "🪡", "culoare": "#C9A227", "text": "Bună"}
    istoric.salveaza_mesaj(mesaj1)
    istoric.salveaza_mesaj(mesaj2)

    raspuns = client.get("/api/mesaje")

    assert raspuns.status_code == 200
    assert raspuns.json() == [mesaj1, mesaj2]
